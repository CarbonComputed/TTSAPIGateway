from flask import Flask, request, send_file, jsonify
from kittentts import KittenTTS
import soundfile as sf
import io
import os
import tempfile
from pydub import AudioSegment
import logging
import re
import numpy as np

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

def normalize_audio(audio_data):
    """Normalize audio to prevent clipping and improve quality"""
    if audio_data is None or len(audio_data) == 0:
        return audio_data
    
    # Convert to float32 if needed
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    
    # Normalize to prevent clipping
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        # Normalize to 0.95 to leave some headroom
        audio_data = audio_data * (0.95 / max_val)
    
    return audio_data

def combine_audio_segments_simple(audio_segments, sample_rate=24000):
    """Combine audio segments using direct numpy concatenation (no format conversion)"""
    if not audio_segments:
        raise ValueError("No audio segments to combine")
    
    if len(audio_segments) == 1:
        return normalize_audio(audio_segments[0])
    
    # Normalize each segment individually to maintain consistent levels
    normalized_segments = []
    for segment in audio_segments:
        # Ensure proper data type
        if segment.dtype != np.float32:
            segment = segment.astype(np.float32)
        
        # Normalize to prevent clipping while maintaining relative levels
        max_val = np.max(np.abs(segment))
        if max_val > 0:
            # Normalize to 0.8 to leave headroom and prevent clipping
            normalized_segment = segment * (0.8 / max_val)
        else:
            normalized_segment = segment
        
        normalized_segments.append(normalized_segment)
    
    # Calculate pause samples (150ms = 3600 samples at 24kHz for better separation)
    pause_samples = int(0.15 * sample_rate)
    pause_audio = np.zeros(pause_samples, dtype=np.float32)
    
    # Combine segments with pauses
    combined = []
    for i, segment in enumerate(normalized_segments):
        if i > 0:
            combined.append(pause_audio)
        combined.append(segment)
    
    # Concatenate all segments
    final_audio = np.concatenate(combined)
    
    
    return final_audio

def combine_audio_segments_advanced(audio_segments, sample_rate=24000):
    """Advanced combination with crossfading and better audio processing"""
    if not audio_segments:
        raise ValueError("No audio segments to combine")
    
    if len(audio_segments) == 1:
        return normalize_audio(audio_segments[0])
    
    # Normalize and prepare segments
    normalized_segments = []
    for segment in audio_segments:
        if segment.dtype != np.float32:
            segment = segment.astype(np.float32)
        
        # Apply gentle normalization
        max_val = np.max(np.abs(segment))
        if max_val > 0:
            normalized_segment = segment * (0.85 / max_val)
        else:
            normalized_segment = segment
        
        normalized_segments.append(normalized_segment)
    
    # Calculate pause with fade in/out for smoother transitions
    pause_samples = int(0.2 * sample_rate)  # 200ms pause
    fade_samples = int(0.01 * sample_rate)  # 10ms fade
    
    # Create pause with fade
    pause_audio = np.zeros(pause_samples, dtype=np.float32)
    
    # Combine with crossfading
    combined = []
    for i, segment in enumerate(normalized_segments):
        if i > 0:
            # Add pause with fade
            combined.append(pause_audio)
        
        # Apply fade in/out to segment
        if len(segment) > 2 * fade_samples:
            # Fade in
            fade_in = np.linspace(0, 1, fade_samples)
            segment[:fade_samples] *= fade_in
            
            # Fade out
            fade_out = np.linspace(1, 0, fade_samples)
            segment[-fade_samples:] *= fade_out
        
        combined.append(segment)
    
    # Concatenate all segments
    final_audio = np.concatenate(combined)
    
    # Final normalization
    final_max = np.max(np.abs(final_audio))
    if final_max > 0:
        final_audio = final_audio * (0.95 / final_max)
    
    return final_audio

def combine_audio_segments_pydub(audio_segments, sample_rate=24000):
    """Combine audio segments using pydub (original method for comparison)"""
    if not audio_segments:
        raise ValueError("No audio segments to combine")
    
    if len(audio_segments) == 1:
        return normalize_audio(audio_segments[0])
    
    # Convert numpy arrays to AudioSegment objects
    combined_audio = None
    for i, audio_data in enumerate(audio_segments):
        # Normalize the audio data
        audio_data = normalize_audio(audio_data)
        
        # Create temporary WAV file for this segment
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            # Save as WAV with proper format
            sf.write(temp_wav.name, audio_data, sample_rate, subtype='PCM_16')
            
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
    
    # Convert back to numpy array with proper format
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
        # Export with high quality settings
        combined_audio.export(temp_wav.name, format='wav', parameters=['-ar', str(sample_rate)])
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
        output_format = data.get('format', 'mp3')  # Output format: mp3, wav, mp4
        use_chunking = data.get('use_chunking', True)  # Enable/disable chunking
        combine_method = data.get('combine_method', 'simple')  # simple, advanced, pydub
        
        # Validate inputs
        if not text:
            return jsonify({'error': 'Text prompt is required'}), 400
        
        if not isinstance(text, str) or len(text.strip()) == 0:
            return jsonify({'error': 'Text must be a non-empty string'}), 400
        
        if voice not in AVAILABLE_VOICES:
            return jsonify({
                'error': f'Invalid voice. Available voices: {AVAILABLE_VOICES}'
            }), 400
        
        if output_format not in ['mp3', 'wav', 'mp4']:
            return jsonify({
                'error': f'Invalid format. Supported formats: mp3, wav, mp4'
            }), 400
        
        if combine_method not in ['simple', 'advanced', 'pydub']:
            return jsonify({
                'error': f'Invalid combine method. Supported methods: simple, advanced, pydub'
            }), 400
        
        # Check if model is loaded
        if model is None:
            return jsonify({'error': 'TTS model not loaded'}), 500
        
        logger.info(f"Generating audio for text: '{text[:50]}...' with voice: {voice}, format: {output_format}, chunking: {use_chunking}, combine: {combine_method}")
        
        if use_chunking:
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
            
            # Combine all audio segments using the specified method
            logger.info("Combining audio segments...")
            if combine_method == 'simple':
                combined_audio = combine_audio_segments_simple(audio_segments)
                logger.info("Used simple combination method")
            elif combine_method == 'advanced':
                combined_audio = combine_audio_segments_advanced(audio_segments)
                logger.info("Used advanced combination method")
            else:  # pydub
                combined_audio = combine_audio_segments_pydub(audio_segments)
                logger.info("Used pydub combination method")
        else:
            # Generate audio for entire text at once (original method)
            logger.info("Generating audio for entire text without chunking")
            combined_audio = generate_sentence_audio(text, voice)
            # combined_audio = normalize_audio(combined_audio)
        
        # Create output buffer
        output_buffer = io.BytesIO()
        
        if output_format == 'wav':
            # Export as WAV with high quality
            sf.write(output_buffer, combined_audio, 24000, subtype='PCM_16', format='WAV')
            mimetype = 'audio/wav'
            extension = 'wav'
        elif output_format == 'mp4':
            # Convert to mp4
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                sf.write(temp_wav.name, combined_audio, 24000)
                audio_segment = AudioSegment.from_wav(temp_wav.name)
                audio_segment.export(output_buffer, format='mp4', bitrate='128k')
                os.unlink(temp_wav.name)
            mimetype = 'audio/mp4'
            extension = 'mp4'
        else:  # mp3
            # Convert to MP3 with high quality settings
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                sf.write(temp_wav.name, combined_audio, 24000)
                audio_segment = AudioSegment.from_wav(temp_wav.name)
                audio_segment.export(output_buffer, format='mp3', bitrate='192k', parameters=['-q:a', '0'])
                os.unlink(temp_wav.name)
            mimetype = 'audio/mpeg'
            extension = 'mp3'
        
        # Reset buffer position
        output_buffer.seek(0)
        
        # Return audio file
        return send_file(
            output_buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=f'generated_audio_{voice}.{extension}'
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