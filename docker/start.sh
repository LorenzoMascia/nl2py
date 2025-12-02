#!/bin/bash
# NL2Py Docker - Start Script

set -e

echo "🚀 Starting NL2Py Docker Environment..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if config file exists
if [ ! -f "config/nl2py.conf" ]; then
    echo "❌ Error: Configuration file not found"
    echo "Please ensure config/nl2py.conf exists"
    exit 1
fi

# Check for OpenAI API key
if grep -q "your-openai-api-key-here" config/nl2py.conf; then
    echo "⚠️  Warning: OpenAI API key not configured"
    echo "Please edit config/nl2py.conf and set your API key"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 Building and starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
echo "   This may take 30-60 seconds..."

# Wait for services
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ NL2Py Docker Environment Started!"
echo ""
echo "🌐 Service URLs:"
echo "   RabbitMQ:    http://localhost:15672  (nl2py/nl2py123)"
echo "   MinIO:       http://localhost:9001   (nl2py/nl2py123)"
echo "   OpenSearch:  https://localhost:9200  (admin/Aibasic123!)"
echo "   MailHog:     http://localhost:8025"
echo ""
echo "🔧 Access NL2Py:"
echo "   docker exec -it nl2py bash"
echo ""
echo "📖 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   ./stop.sh"
echo ""
