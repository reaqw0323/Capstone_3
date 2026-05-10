$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "EasyPick AI start script" -ForegroundColor Cyan
Write-Host "Checking Docker and GPU environment..." -ForegroundColor Cyan

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "docker")) {
    Write-Host "Docker command was not found. Install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    docker info *> $null
} catch {
    Write-Host "Docker Desktop is not running. Start Docker Desktop and run this script again." -ForegroundColor Red
    exit 1
}

$useGpu = $false
if (Test-CommandExists "nvidia-smi") {
    try {
        nvidia-smi *> $null
        $useGpu = $true
    } catch {
        $useGpu = $false
    }
}

$composeArgs = @("-f", "docker-compose.yml")

if ($useGpu) {
    Write-Host "NVIDIA GPU detected. Ollama will run with GPU acceleration." -ForegroundColor Green
    $composeArgs += @("-f", "docker-compose.gpu.yml")
} else {
    Write-Host "No NVIDIA GPU detected. Ollama will run in CPU mode." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting EasyPick services..." -ForegroundColor Cyan
docker compose @composeArgs up -d --build

Write-Host ""
Write-Host "Preparing Ollama model. The first run can take several minutes." -ForegroundColor Cyan
docker compose @composeArgs up ollama-init

Write-Host ""
Write-Host "EasyPick AI is ready." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend docs: http://localhost:8000/docs"
Write-Host ""
