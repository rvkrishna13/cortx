#!/bin/bash
# Script to prepare environment for demo video recording

echo "🎬 Preparing Demo Environment..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
echo "📦 Starting Docker services..."
make docker-up > /dev/null 2>&1

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Generate admin token
echo "🔑 Generating admin token..."
ADMIN_TOKEN=$(python3 scripts/generate_admin_token.py 2>/dev/null | grep -oP 'Bearer \K[^\s]+' || python3 scripts/generate_admin_token.py 2>/dev/null | tail -1)
echo "Admin Token: $ADMIN_TOKEN"
echo ""

# Create viewer token (if script exists)
if [ -f "scripts/generate_viewer_token.py" ]; then
    echo "🔑 Generating viewer token..."
    VIEWER_TOKEN=$(python3 scripts/generate_viewer_token.py 2>/dev/null | grep -oP 'Bearer \K[^\s]+' || python3 scripts/generate_viewer_token.py 2>/dev/null | tail -1)
    echo "Viewer Token: $VIEWER_TOKEN"
    echo ""
fi

# Make a test request to generate metrics/logs
echo "🧪 Making test request to generate metrics..."
curl -s -X POST http://localhost:8000/api/v1/reasoning \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Get market summary for AAPL", "include_thinking": true}' > /dev/null

echo ""
echo "✅ Demo environment ready!"
echo ""
echo "📋 Quick Reference:"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "🔑 Admin Token:"
echo "  $ADMIN_TOKEN"
echo ""
echo "📝 Save these tokens for the demo!"
echo ""
echo "🎥 You're ready to record!"

