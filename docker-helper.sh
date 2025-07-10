#!/bin/bash

# Docker helper script for Utku Optik Scraper
# Usage: ./docker-helper.sh [command]

set -e

PROJECT_NAME="utku-optik-scraper"
COMPOSE_FILE="docker-compose.yml"
DEV_COMPOSE_FILE="docker-compose.dev.yml"

show_help() {
    echo "Utku Optik Scraper - Docker Helper"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image"
    echo "  run         Run the scraper once"
    echo "  start       Start the scraper in background"
    echo "  stop        Stop the scraper"
    echo "  logs        Show logs"
    echo "  status      Show container status"
    echo "  clean       Clean up containers and images"
    echo "  dev         Run in development mode"
    echo "  monitor     Start with monitoring dashboard"
    echo "  health      Run health check"
    echo "  shell       Open shell in container"
    echo "  help        Show this help message"
    echo ""
}

check_env() {
    if [ ! -f .env ]; then
        echo "⚠️  .env file not found. Creating from template..."
        cp .env.example .env
        echo "📝 Please edit .env file with your credentials before running."
        exit 1
    fi
}

case "${1:-help}" in
    build)
        echo "🔨 Building Docker image..."
        docker compose build
        ;;
    run)
        echo "🚀 Running scraper..."
        check_env
        docker compose up scraper
        ;;
    start)
        echo "🚀 Starting scraper in background..."
        check_env
        docker compose up -d scraper
        echo "✅ Scraper started. Use '$0 logs' to view progress."
        ;;
    stop)
        echo "🛑 Stopping scraper..."
        docker compose down
        ;;
    logs)
        echo "📋 Showing logs..."
        docker compose logs -f scraper
        ;;
    status)
        echo "📊 Container status:"
        docker compose ps
        ;;
    clean)
        echo "🧹 Cleaning up..."
        docker compose down --rmi all --volumes --remove-orphans
        docker system prune -f
        ;;
    dev)
        echo "🔧 Running in development mode..."
        check_env
        docker compose -f $DEV_COMPOSE_FILE up
        ;;
    monitor)
        echo "📊 Starting with monitoring dashboard..."
        check_env
        docker compose --profile monitoring up -d
        echo "✅ Monitoring available at http://localhost:8000"
        ;;
    health)
        echo "🏥 Running health check..."
        docker compose run --rm scraper python health_check.py
        ;;
    shell)
        echo "🐚 Opening shell in container..."
        docker compose exec scraper /bin/bash
        ;;
    help)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_help
        exit 1
        ;;
esac
