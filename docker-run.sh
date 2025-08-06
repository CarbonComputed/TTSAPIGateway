#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐳 TTS API Gateway Docker Setup${NC}"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  docker-compose not found. Using docker build and run instead.${NC}"
    USE_COMPOSE=false
else
    USE_COMPOSE=true
fi

# Create audio_output directory if it doesn't exist
mkdir -p audio_output

if [ "$USE_COMPOSE" = true ]; then
    echo -e "${GREEN}📦 Building and starting with docker-compose...${NC}"
    
    # Build and start with docker-compose
    docker-compose up --build -d
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Container started successfully!${NC}"
        echo ""
        echo -e "${YELLOW}📋 Container Status:${NC}"
        docker-compose ps
        echo ""
        echo -e "${YELLOW}📋 Logs:${NC}"
        docker-compose logs -f --tail=20
    else
        echo -e "${RED}❌ Failed to start container${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}📦 Building Docker image...${NC}"
    
    # Build the image
    docker build -t tts-api-gateway .
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to build Docker image${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}🚀 Starting container...${NC}"
    
    # Run the container
    docker run -d \
        --name tts-api-gateway \
        -p 5050:5050 \
        -v $(pwd)/audio_output:/app/audio_output \
        --restart unless-stopped \
        tts-api-gateway
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Container started successfully!${NC}"
        echo ""
        echo -e "${YELLOW}📋 Container Status:${NC}"
        docker ps --filter name=tts-api-gateway
        echo ""
        echo -e "${YELLOW}📋 Logs:${NC}"
        docker logs -f tts-api-gateway
    else
        echo -e "${RED}❌ Failed to start container${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎯 API is now available at: http://localhost:5050${NC}"
echo -e "${YELLOW}📝 API Endpoints:${NC}"
echo "   - Health check: GET http://localhost:5050/health"
echo "   - Get voices: GET http://localhost:5050/voices"
echo "   - Generate audio: POST http://localhost:5050/generate"
echo ""
echo -e "${YELLOW}🛑 To stop the container:${NC}"
if [ "$USE_COMPOSE" = true ]; then
    echo "   docker-compose down"
else
    echo "   docker stop tts-api-gateway"
fi 