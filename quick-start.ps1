# Quick Start Script for Utku Optik Scraper (PowerShell)
# This script will set up and run the scraper with minimal configuration

Write-Host "🚀 Utku Optik Scraper - Quick Start" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Check if Docker is installed
try {
    docker --version | Out-Null
    docker-compose --version | Out-Null
} catch {
    Write-Host "❌ Docker or Docker Compose is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "📝 Setting up environment file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Please edit the .env file with your credentials:" -ForegroundColor Red
    Write-Host "   - SFTP_USERNAME: Your Google Merchant Center username" -ForegroundColor White
    Write-Host "   - SFTP_PASSWORD: Your Google Merchant Center password" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter after editing the .env file"
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Build the Docker image
Write-Host "🔨 Building Docker image..." -ForegroundColor Blue
docker-compose build

# Run the scraper
Write-Host "🚀 Starting scraper..." -ForegroundColor Green
docker-compose up scraper

Write-Host "✅ Done! Check the 'data' directory for output files." -ForegroundColor Green
