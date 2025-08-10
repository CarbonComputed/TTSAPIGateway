from flask import Flask, request, send_file, jsonify
from kittentts import KittenTTS
import soundfile as sf
import io
import os
import tempfile
from pydub import AudioSegment
import logging
import re

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize KittenTTS model
try:
    model = KittenTTS("KittenML/kitten-tts-nano-0.1")
    logger.info("KittenTTS model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load KittenTTS model: {e}")
    model = None

# Available voices from the KittenTTS documentation
AVAILABLE_VOICES = [
    'expr-voice-2-m', 'expr-voice-2-f', 'expr-voice-3-m', 'expr-voice-3-f',
    'expr-voice-4-m', 'expr-voice-4-f', 'expr-voice-5-m', 'expr-voice-5-f'
]

def split_into_sentences(text):
    """Split text into sentences using regex (fallback method)"""
    # Split on sentence endings (.!?) followed by whitespace or end of string
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter out empty sentences and clean up
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def split_text_with_spacy(text, max_chars=400, max_words=50):
    """Split text using spaCy for better sentence detection with length limits"""
    try:
        import spacy
        # Load spaCy model (will download if not available)
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy English model not found. Installing...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
            nlp = spacy.load("en_core_web_sm")
        
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]
        
        # Apply length limits to sentences
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Check if adding this sentence would exceed limits
            if (len(current_chunk + sentence) > max_chars or 
                len((current_chunk + sentence).split()) > max_words):
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too long, split by words
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk + word) <= max_chars and len(temp_chunk.split()) < max_words:
                            temp_chunk += " " + word if temp_chunk else word
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                chunks.append(word)
                    current_chunk = temp_chunk
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]
        
    except Exception as e:
        logger.warning(f"spaCy failed, falling back to regex: {e}")
        return split_into_sentences(text)

def generate_sentence_audio(sentence, voice):
    """Generate audio for a single sentence"""
    try:
        audio = model.generate(sentence, voice=voice)
        return audio
    except Exception as e:
        logger.error(f"Error generating audio for sentence '{sentence[:30]}...': {e}")
        raise

def combine_audio_segments(audio_segments, sample_rate=24000):
    """Combine multiple audio segments into one"""
    if not audio_segments:
        raise ValueError("No audio segments to combine")
    
    if len(audio_segments) == 1:
        return audio_segments[0]
    
    # Convert numpy arrays to AudioSegment objects
    combined_audio = None
    for i, audio_data in enumerate(audio_segments):
        # Create temporary WAV file for this segment
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            sf.write(temp_wav.name, audio_data, sample_rate)
            
            # Load as AudioSegment
            segment = AudioSegment.from_wav(temp_wav.name)
            
            # Add small pause between sentences (100ms)
            if i > 0:
                pause = AudioSegment.silent(duration=100)
                segment = pause + segment
            
            # Combine with previous segments
            if combined_audio is None:
                combined_audio = segment
            else:
                combined_audio += segment
            
            # Clean up temporary file
            os.unlink(temp_wav.name)
    
    # Convert back to numpy array
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
        combined_audio.export(temp_wav.name, format='wav')
        audio_data, _ = sf.read(temp_wav.name)
        os.unlink(temp_wav.name)
        return audio_data

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'available_voices': AVAILABLE_VOICES
    })

@app.route('/generate', methods=['POST'])
def generate_audio():
    """Generate audio from text prompt"""
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text')
        voice = data.get('voice', 'expr-voice-2-f')  # Default voice
        max_chars = data.get('max_chars', 400)  # Configurable character limit
        max_words = data.get('max_words', 50)   # Configurable word limit
        
        # Validate inputs
        if not text:
            return jsonify({'error': 'Text prompt is required'}), 400
        
        if not isinstance(text, str) or len(text.strip()) == 0:
            return jsonify({'error': 'Text must be a non-empty string'}), 400
        
        if voice not in AVAILABLE_VOICES:
            return jsonify({
                'error': f'Invalid voice. Available voices: {AVAILABLE_VOICES}'
            }), 400
        
        # Check if model is loaded
        if model is None:
            return jsonify({'error': 'TTS model not loaded'}), 500
        
        logger.info(f"Generating audio for text: '{text[:50]}...' with voice: {voice}")
        
        # Split text using spaCy with length limits
        chunks = split_text_with_spacy(text, max_chars, max_words)
        logger.info(f"Split text into {len(chunks)} chunks using spaCy")
        
        if len(chunks) == 0:
            return jsonify({'error': 'No valid text chunks found'}), 400
        
        # Generate audio for each chunk
        audio_segments = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}: '{chunk[:30]}...'")
            try:
                audio_segment = generate_sentence_audio(chunk, voice)
                audio_segments.append(audio_segment)
            except Exception as e:
                logger.error(f"Failed to generate audio for chunk {i+1}: {e}")
                return jsonify({'error': f'Failed to generate audio for chunk {i+1}: {str(e)}'}), 500
        
        # Combine all audio segments
        logger.info("Combining audio segments...")
        combined_audio = combine_audio_segments(audio_segments)
        
        # Create temporary file for WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            # Save as WAV first (KittenTTS outputs at 24kHz)
            sf.write(temp_wav.name, combined_audio, 24000)
            
            # Convert WAV to MP3 using pydub
            audio_segment = AudioSegment.from_wav(temp_wav.name)
            
            # Create output buffer
            output_buffer = io.BytesIO()
            
            # Export as MP3
            audio_segment.export(output_buffer, format='mp3', bitrate='128k')
            
            # Clean up WAV file
            os.unlink(temp_wav.name)
            
            # Reset buffer position
            output_buffer.seek(0)
            
            # Return MP3 file
            return send_file(
                output_buffer,
                mimetype='audio/mpeg',
                as_attachment=True,
                download_name=f'generated_audio_{voice}.mp3'
            )
    
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        return jsonify({'error': f'Failed to generate audio: {str(e)}'}), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get list of available voices"""
    return jsonify({
        'voices': AVAILABLE_VOICES,
        'count': len(AVAILABLE_VOICES)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Use 0.0.0.0 to bind to all interfaces in Docker
    app.run(debug=False, host='0.0.0.0', port=5050) 