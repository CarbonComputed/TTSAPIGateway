#!/bin/bash

echo "🚀 Starting TTS API Gateway..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies. Please check the requirements.txt file."
        exit 1
    fi
else
    echo "❌ requirements.txt not found. Please make sure you're in the correct directory."
    exit 1
fi

# Start the server
echo "🎯 Starting Flask server on http://localhost:5050"
echo "📝 API Documentation:"
echo "   - Health check: GET http://localhost:5050/health"
echo "   - Get voices: GET http://localhost:5050/voices"
echo "   - Generate audio: POST http://localhost:5050/generate"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py 