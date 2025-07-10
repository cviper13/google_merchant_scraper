#!/bin/bash

# Quick Start Script for Utku Optik Scraper
# This script will set up and run the scraper with minimal configuration

set -e

echo "🚀 Utku Optik Scraper - Quick Start"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Setting up environment file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit the .env file with your credentials:"
    echo "   - SFTP_USERNAME: Your Google Merchant Center username"
    echo "   - SFTP_PASSWORD: Your Google Merchant Center password"
    echo ""
    read -p "Press Enter after editing the .env file..."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Build the Docker image
echo "🔨 Building Docker image..."
docker-compose build

# Run the scraper
echo "🚀 Starting scraper..."
docker-compose up scraper

echo "✅ Done! Check the 'data' directory for output files."
