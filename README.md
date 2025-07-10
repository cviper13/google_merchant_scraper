# Utku Optik Google Merchant Scraper

A Docker-friendly web scraper for Utku Optik sunglasses that generates Google Merchant Center compatible product feeds.

## Features

- 🐳 **Docker Support**: Full containerization with Docker and Docker Compose
- 📦 **Google Merchant Center Integration**: Direct SFTP upload to Google Merchant Center
- ⚡ **Multi-threaded Scraping**: Concurrent processing for faster scraping
- 🔄 **Retry Logic**: Automatic retry of failed requests
- 📊 **Multiple Output Formats**: TSV (Google Merchant) and JSON formats
- 🛡️ **Robust Error Handling**: Comprehensive logging and error recovery
- 🌐 **Environment Configuration**: Easy configuration via environment variables

## Quick Start with Docker

### 1. Clone and Setup

```bash
git clone <repository-url>
cd google_merchant_scraper
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your credentials
# At minimum, you need to set:
# SFTP_USERNAME=your_google_merchant_username
# SFTP_PASSWORD=your_google_merchant_password
```

### 3. Build and Run

```bash
# Build the Docker image
docker-compose build

# Run the scraper
docker-compose up scraper

# Or run in detached mode
docker-compose up -d scraper
```

### 4. Optional: Monitor with Web Interface

```bash
# Start with monitoring dashboard
docker-compose --profile monitoring up -d

# Access the dashboard at http://localhost:8000
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SFTP_HOST` | `partnerupload.google.com` | Google Merchant SFTP host |
| `SFTP_PORT` | `19321` | SFTP port |
| `SFTP_USERNAME` | - | **Required**: Your Google Merchant username |
| `SFTP_PASSWORD` | - | **Required**: Your Google Merchant password |
| `SCRAPE_LINKS` | `true` | Whether to scrape product links first |
| `MAX_WORKERS` | `8` | Number of concurrent workers |
| `DELAY` | `0.1` | Delay between requests (seconds) |
| `ENABLE_RETRY` | `true` | Enable retry logic for failed requests |
| `UPLOAD_TO_SFTP` | `true` | Upload results to Google Merchant Center |
| `BASE_URL` | `https://www.utkuoptik.com` | Base URL for scraping |
| `CATEGORY_URL` | `{BASE_URL}/kategori/gunes-gozlukleri-54/` | Category page URL |
| `TOTAL_PAGES` | `25` | Number of pages to scrape |

## Docker Commands

### Basic Usage

```bash
# Build the image
docker-compose build

# Run once
docker-compose up scraper

# Run in background
docker-compose up -d scraper

# View logs
docker-compose logs -f scraper

# Stop
docker-compose down
```

### Advanced Usage

```bash
# Run with custom configuration
docker-compose run -e MAX_WORKERS=12 -e DELAY=0.05 scraper

# Run only link scraping
docker-compose run -e SCRAPE_LINKS=true -e UPLOAD_TO_SFTP=false scraper

# Run with monitoring
docker-compose --profile monitoring up -d
```

### Development

```bash
# Run with volume mounting for development
docker-compose -f docker-compose.dev.yml up

# Access container shell
docker-compose exec scraper /bin/bash

# Run tests
docker-compose run scraper python -m pytest
```

## Manual Installation (Non-Docker)

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone repository
git clone <repository-url>
cd google_merchant_scraper

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
# Run scraper
python main.py
```

## Output Files

The scraper generates the following files in the `.data/` directory:

- `product_links.txt`: List of all product URLs
- `google_merchant_products.tsv`: Google Merchant Center compatible feed
- `google_merchant_products.json`: JSON format of all products

## Data Directory Structure

```
.data/
├── product_links.txt          # Product URLs
├── google_merchant_products.tsv  # Google Merchant feed
└── google_merchant_products.json # JSON export

logs/
└── scraper.log               # Application logs
```

## Google Merchant Center Integration

The scraper automatically uploads the TSV file to Google Merchant Center via SFTP. Make sure to:

1. Set up your Google Merchant Center account
2. Configure SFTP access in your Google Merchant Center settings
3. Add your SFTP credentials to the `.env` file

## Troubleshooting

### Common Issues

1. **SFTP Authentication Failed**
   - Check your `SFTP_USERNAME` and `SFTP_PASSWORD` in `.env`
   - Verify SFTP is enabled in your Google Merchant Center account

2. **Permission Denied**
   - Ensure the `data` directory is writable
   - Check Docker volume permissions

3. **Connection Timeouts**
   - Reduce `MAX_WORKERS` in your environment
   - Increase `DELAY` between requests

### Viewing Logs

```bash
# Docker logs
docker-compose logs -f scraper

# Log files
tail -f logs/scraper.log
```

### Health Check

```bash
# Check container health
docker-compose ps

# Manual health check
docker-compose exec scraper python -c "import requests; print('healthy')"
```

## Configuration Examples

### High Performance (Use with caution)

```bash
# .env
MAX_WORKERS=16
DELAY=0.05
ENABLE_RETRY=true
```

### Conservative (Recommended for production)

```bash
# .env
MAX_WORKERS=4
DELAY=0.2
ENABLE_RETRY=true
```

### Development/Testing

```bash
# .env
MAX_WORKERS=2
DELAY=0.5
UPLOAD_TO_SFTP=false
SCRAPE_LINKS=false  # Use existing product_links.txt
```

## Security Notes

- Never commit your `.env` file to version control
- Use strong passwords for SFTP access
- Consider using Docker secrets for production deployments
- The container runs as a non-root user for security

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the logs: `docker-compose logs scraper`
2. Review the troubleshooting section
3. Open an issue on GitHub
