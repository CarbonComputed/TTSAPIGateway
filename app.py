from flask import Flask, request, send_file, jsonify
from kittentts import KittenTTS
import soundfile as sf
import io
import os
import tempfile
from pydub import AudioSegment
import logging

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
        
        # Generate audio using KittenTTS
        audio = model.generate(text, voice=voice)
        
        # Create temporary file for WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            # Save as WAV first (KittenTTS outputs at 24kHz)
            sf.write(temp_wav.name, audio, 24000)
            
            # Convert WAV to AAC using pydub
            audio_segment = AudioSegment.from_wav(temp_wav.name)
            
            # Create temporary file for AAC
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_aac:
                # Export as AAC
                audio_segment.export(temp_aac.name, format='mp4', bitrate='128k')
                
                # Clean up WAV file
                os.unlink(temp_wav.name)
                
                # Return AAC file
                return send_file(
                    temp_aac.name,
                    mimetype='audio/mp4',
                    as_attachment=True,
                    download_name=f'generated_audio_{voice}.mp4'
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