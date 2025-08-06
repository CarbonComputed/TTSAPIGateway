# TTS API Gateway

A Flask-based API server that uses [KittenTTS](https://github.com/KittenML/KittenTTS) to generate high-quality audio from text prompts. The server returns AAC audio files for easy integration with various applications.

## Features

- **Ultra-lightweight TTS**: Uses KittenTTS model under 25MB
- **Multiple Voices**: 8 different voice options (male and female)
- **AAC Output**: Returns compressed AAC audio files
- **RESTful API**: Simple HTTP endpoints for easy integration
- **Error Handling**: Comprehensive error handling and validation
- **Health Monitoring**: Built-in health check endpoint

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd TTSAPIGateway
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### Health Check
**GET** `/health`

Check if the server and TTS model are working properly.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "available_voices": ["expr-voice-2-m", "expr-voice-2-f", ...]
}
```

### Get Available Voices
**GET** `/voices`

Get a list of all available voice options.

**Response:**
```json
{
  "voices": ["expr-voice-2-m", "expr-voice-2-f", "expr-voice-3-m", "expr-voice-3-f", "expr-voice-4-m", "expr-voice-4-f", "expr-voice-5-m", "expr-voice-5-f"],
  "count": 8
}
```

### Generate Audio
**POST** `/generate`

Generate audio from text prompt.

**Request Body:**
```json
{
  "text": "Hello, this is a test of the text-to-speech system.",
  "voice": "expr-voice-2-f"
}
```

**Parameters:**
- `text` (required): The text to convert to speech
- `voice` (optional): Voice to use (defaults to "expr-voice-2-f")

**Response:**
Returns an AAC audio file as an attachment.

## Usage Examples

### Using curl

```bash
# Health check
curl http://localhost:5000/health

# Get available voices
curl http://localhost:5000/voices

# Generate audio
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world!", "voice": "expr-voice-2-f"}' \
  --output output.aac
```

### Using Python requests

```python
import requests

# Generate audio
response = requests.post('http://localhost:5000/generate', 
    json={
        'text': 'Hello, this is a test message.',
        'voice': 'expr-voice-2-f'
    }
)

if response.status_code == 200:
    with open('output.aac', 'wb') as f:
        f.write(response.content)
    print("Audio saved as output.aac")
else:
    print(f"Error: {response.json()}")
```

### Using JavaScript fetch

```javascript
// Generate audio
fetch('http://localhost:5000/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        text: 'Hello from JavaScript!',
        voice: 'expr-voice-2-f'
    })
})
.then(response => {
    if (response.ok) {
        return response.blob();
    }
    throw new Error('Network response was not ok');
})
.then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'generated_audio.aac';
    a.click();
});
```

## Available Voices

The server supports 8 different voices:

- `expr-voice-2-m` - Male voice 2
- `expr-voice-2-f` - Female voice 2 (default)
- `expr-voice-3-m` - Male voice 3
- `expr-voice-3-f` - Female voice 3
- `expr-voice-4-m` - Male voice 4
- `expr-voice-4-f` - Female voice 4
- `expr-voice-5-m` - Male voice 5
- `expr-voice-5-f` - Female voice 5

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `400 Bad Request`: Invalid input (missing text, invalid voice, etc.)
- `500 Internal Server Error`: Server-side errors (model not loaded, generation failed, etc.)

Error responses include a JSON object with an `error` field describing the issue.

## System Requirements

- Python 3.8+
- Sufficient RAM for the TTS model (~100MB)
- Internet connection for initial model download

## Production Deployment

For production use, consider:

1. Using a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. Adding environment variables for configuration
3. Implementing rate limiting
4. Adding authentication if needed
5. Using a reverse proxy like Nginx

## License

This project uses KittenTTS which is licensed under Apache-2.0.

## Contributing

Feel free to submit issues and enhancement requests!