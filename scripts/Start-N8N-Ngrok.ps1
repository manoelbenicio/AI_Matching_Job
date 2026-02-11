# =============================================================================
# n8n + ngrok Auto-Start Script for Windows
# =============================================================================
# Run this script to:
# 1. Kill any existing ngrok processes
# 2. Start a new ngrok tunnel on port 5678
# 3. Get the new ngrok URL  
# 4. Restart n8n container with updated WEBHOOK_URL
# =============================================================================

$N8N_CONTAINER = "n8n-jobs"
$N8N_PORT = 5678
$NGROK_WAIT_TIME = 5

Write-Host "========================================"
Write-Host "🚀 n8n + ngrok Auto-Start Script" -ForegroundColor Cyan
Write-Host "========================================"

# Step 1: Kill existing ngrok processes
Write-Host ""
Write-Host "📦 Step 1: Cleaning up existing ngrok..." -ForegroundColor Yellow
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Step 2: Start ngrok in background
Write-Host ""
Write-Host "🌐 Step 2: Starting ngrok tunnel on port $N8N_PORT..." -ForegroundColor Yellow
Start-Process -FilePath "ngrok" -ArgumentList "http", $N8N_PORT -WindowStyle Hidden
Write-Host "   ngrok started in background"

# Wait for ngrok to initialize
Write-Host "   Waiting ${NGROK_WAIT_TIME}s for ngrok to initialize..."
Start-Sleep -Seconds $NGROK_WAIT_TIME

# Step 3: Get the new ngrok URL
Write-Host ""
Write-Host "🔗 Step 3: Fetching ngrok public URL..." -ForegroundColor Yellow
try {
    $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
    $NGROK_URL = ($tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
    
    if ([string]::IsNullOrEmpty($NGROK_URL)) {
        $NGROK_URL = $tunnels.tunnels[0].public_url
    }
} catch {
    Write-Host "❌ ERROR: Failed to get ngrok URL!" -ForegroundColor Red
    Write-Host "   Check if ngrok is running: http://localhost:4040"
    exit 1
}

Write-Host "   ✅ ngrok URL: $NGROK_URL" -ForegroundColor Green

# Step 4: Stop existing n8n container
Write-Host ""
Write-Host "🛑 Step 4: Stopping existing n8n container..." -ForegroundColor Yellow
wsl docker stop $N8N_CONTAINER 2>$null
wsl docker rm $N8N_CONTAINER 2>$null

# Step 5: Start n8n with updated WEBHOOK_URL
Write-Host ""
Write-Host "🐳 Step 5: Starting n8n container with new WEBHOOK_URL..." -ForegroundColor Yellow
$dockerCmd = @"
docker run -d --name $N8N_CONTAINER --restart unless-stopped -p 5678:5678 -v n8n_data:/home/node/.n8n -e WEBHOOK_URL=$NGROK_URL -e N8N_HOST=0.0.0.0 -e N8N_PORT=5678 -e N8N_PROTOCOL=https -e GENERIC_TIMEZONE=America/Sao_Paulo -e TZ=America/Sao_Paulo n8nio/n8n:latest
"@
wsl bash -c $dockerCmd

# Step 6: Wait for n8n to be ready
Write-Host ""
Write-Host "⏳ Step 6: Waiting for n8n to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Verify
Write-Host ""
Write-Host "========================================"
Write-Host "✅ SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""
Write-Host "📌 Your URLs:" -ForegroundColor Cyan
Write-Host "   Local:  http://localhost:5678"
Write-Host "   Public: $NGROK_URL"
Write-Host ""
Write-Host "📌 Container Status:" -ForegroundColor Cyan
wsl docker ps --filter "name=$N8N_CONTAINER" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""
Write-Host "📌 WEBHOOK_URL in container:" -ForegroundColor Cyan
wsl docker exec $N8N_CONTAINER printenv WEBHOOK_URL
Write-Host ""
Write-Host "========================================"

# Save URL to file
$NGROK_URL | Out-File -FilePath ".\ngrok_url.txt" -Encoding UTF8
Write-Host "📁 URL saved to: .\ngrok_url.txt" -ForegroundColor Green

# Keep the window open
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
