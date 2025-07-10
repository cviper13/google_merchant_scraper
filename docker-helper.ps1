# PowerShell helper script for Utku Optik Scraper
# Usage: .\docker-helper.ps1 [command]

param(
    [string]$Command = "help"
)

$ProjectName = "utku-optik-scraper"
$ComposeFile = "docker-compose.yml"
$DevComposeFile = "docker-compose.dev.yml"

function Show-Help {
    Write-Host "Utku Optik Scraper - Docker Helper" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\docker-helper.ps1 [command]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  build       Build the Docker image" -ForegroundColor White
    Write-Host "  run         Run the scraper once" -ForegroundColor White
    Write-Host "  start       Start the scraper in background" -ForegroundColor White
    Write-Host "  stop        Stop the scraper" -ForegroundColor White
    Write-Host "  logs        Show logs" -ForegroundColor White
    Write-Host "  status      Show container status" -ForegroundColor White
    Write-Host "  clean       Clean up containers and images" -ForegroundColor White
    Write-Host "  dev         Run in development mode" -ForegroundColor White
    Write-Host "  monitor     Start with monitoring dashboard" -ForegroundColor White
    Write-Host "  health      Run health check" -ForegroundColor White
    Write-Host "  shell       Open shell in container" -ForegroundColor White
    Write-Host "  help        Show this help message" -ForegroundColor White
    Write-Host ""
}

function Check-Environment {
    if (-not (Test-Path ".env")) {
        Write-Host "⚠️  .env file not found. Creating from template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "📝 Please edit .env file with your credentials before running." -ForegroundColor Red
        exit 1
    }
}

switch ($Command.ToLower()) {
    "build" {
        Write-Host "🔨 Building Docker image..." -ForegroundColor Blue
        docker-compose build
    }
    "run" {
        Write-Host "🚀 Running scraper..." -ForegroundColor Green
        Check-Environment
        docker-compose up scraper
    }
    "start" {
        Write-Host "🚀 Starting scraper in background..." -ForegroundColor Green
        Check-Environment
        docker-compose up -d scraper
        Write-Host "✅ Scraper started. Use '.\docker-helper.ps1 logs' to view progress." -ForegroundColor Green
    }
    "stop" {
        Write-Host "🛑 Stopping scraper..." -ForegroundColor Red
        docker-compose down
    }
    "logs" {
        Write-Host "📋 Showing logs..." -ForegroundColor Blue
        docker-compose logs -f scraper
    }
    "status" {
        Write-Host "📊 Container status:" -ForegroundColor Blue
        docker-compose ps
    }
    "clean" {
        Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
        docker-compose down --rmi all --volumes --remove-orphans
        docker system prune -f
    }
    "dev" {
        Write-Host "🔧 Running in development mode..." -ForegroundColor Magenta
        Check-Environment
        docker-compose -f $DevComposeFile up
    }
    "monitor" {
        Write-Host "📊 Starting with monitoring dashboard..." -ForegroundColor Blue
        Check-Environment
        docker-compose --profile monitoring up -d
        Write-Host "✅ Monitoring available at http://localhost:8000" -ForegroundColor Green
    }
    "health" {
        Write-Host "🏥 Running health check..." -ForegroundColor Blue
        docker-compose run --rm scraper python health_check.py
    }
    "shell" {
        Write-Host "🐚 Opening shell in container..." -ForegroundColor Blue
        docker-compose exec scraper /bin/bash
    }
    "help" {
        Show-Help
    }
    default {
        Write-Host "❌ Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
