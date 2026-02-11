#!/bin/bash
# =============================================================================
# n8n + ngrok Auto-Start Script
# =============================================================================
# This script:
# 1. Kills any existing ngrok process
# 2. Starts a new ngrok tunnel on port 5678
# 3. Gets the new ngrok URL
# 4. Restarts n8n container with updated WEBHOOK_URL
# =============================================================================

set -e

N8N_CONTAINER="n8n-jobs"
N8N_PORT=5678
NGROK_WAIT_TIME=5

echo "========================================"
echo "🚀 n8n + ngrok Auto-Start Script"
echo "========================================"

# Step 1: Kill existing ngrok processes
echo ""
echo "📦 Step 1: Cleaning up existing ngrok..."
pkill -f ngrok 2>/dev/null || true
sleep 1

# Step 2: Start ngrok in background
echo ""
echo "🌐 Step 2: Starting ngrok tunnel on port $N8N_PORT..."
nohup ngrok http $N8N_PORT > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
echo "   ngrok started with PID: $NGROK_PID"

# Wait for ngrok to initialize
echo "   Waiting ${NGROK_WAIT_TIME}s for ngrok to initialize..."
sleep $NGROK_WAIT_TIME

# Step 3: Get the new ngrok URL
echo ""
echo "🔗 Step 3: Fetching ngrok public URL..."
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -oP 'https://[^"]+' | head -1)

if [ -z "$NGROK_URL" ]; then
    echo "❌ ERROR: Failed to get ngrok URL!"
    echo "   Check ngrok logs: cat /tmp/ngrok.log"
    exit 1
fi

echo "   ✅ ngrok URL: $NGROK_URL"

# Step 4: Stop existing n8n container
echo ""
echo "🛑 Step 4: Stopping existing n8n container..."
docker stop $N8N_CONTAINER 2>/dev/null || true
docker rm $N8N_CONTAINER 2>/dev/null || true

# Step 5: Start n8n with updated WEBHOOK_URL
echo ""
echo "🐳 Step 5: Starting n8n container with new WEBHOOK_URL..."
docker run -d \
    --name $N8N_CONTAINER \
    --restart unless-stopped \
    -p 5678:5678 \
    -v n8n_data:/home/node/.n8n \
    -e WEBHOOK_URL=$NGROK_URL \
    -e N8N_HOST=0.0.0.0 \
    -e N8N_PORT=5678 \
    -e N8N_PROTOCOL=https \
    -e GENERIC_TIMEZONE=America/Sao_Paulo \
    -e TZ=America/Sao_Paulo \
    n8nio/n8n:latest

# Step 6: Wait for n8n to be ready
echo ""
echo "⏳ Step 6: Waiting for n8n to be ready..."
sleep 5

# Verify
echo ""
echo "========================================"
echo "✅ SETUP COMPLETE!"
echo "========================================"
echo ""
echo "📌 Your URLs:"
echo "   Local:  http://localhost:5678"
echo "   Public: $NGROK_URL"
echo ""
echo "📌 Container Status:"
docker ps --filter "name=$N8N_CONTAINER" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "📌 WEBHOOK_URL in container:"
docker exec $N8N_CONTAINER printenv WEBHOOK_URL
echo ""
echo "========================================"

# Save URL to file for reference
echo $NGROK_URL > /tmp/n8n_ngrok_url.txt
echo "📁 URL saved to: /tmp/n8n_ngrok_url.txt"
