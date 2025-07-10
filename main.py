import requests
from bs4 import BeautifulSoup
import csv
import re
from urllib.parse import urljoin, urlparse
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import paramiko
import os
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Set up logging with file and console handlers
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(log_dir / 'scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Handle graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@dataclass
class ProductInfo:
    id: str = ""
    title: str = ""
    description: str = ""
    link: str = ""
    image_link: str = ""
    additional_image_link: str = ""
    availability: str = ""
    price: str = ""
    sale_price: str = ""
    brand: str = ""
    mpn: str = ""
    gtin: str = ""
    google_product_category: str = ""
    condition: str = ""
    adult: str = ""
    gender: str = ""
    age_group: str = ""

class CombinedUtkuOptikScraper:
    def __init__(self, base_url: str = None, max_workers: int = None, timeout: int = 15):
        self.base_url = base_url or os.getenv('BASE_URL', "https://www.utkuoptik.com")
        self.max_workers = max_workers or int(os.getenv('MAX_WORKERS', '10'))
        self.timeout = timeout
        self.session_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.scraped_count = 0
        self.total_count = 0
        
        # Thread-local storage for sessions
        self.local_data = threading.local()
        
        # Results storage
        self.results = []
        self.results_lock = threading.Lock()
        
        # Failed URLs for retry
        self.failed_urls = Queue()
        
        # Category scraping settings (configurable via environment)
        self.category_url = os.getenv('CATEGORY_URL', self.base_url + "/kategori/gunes-gozlukleri-54/")
        self.total_pages = int(os.getenv('TOTAL_PAGES', '25'))
        
        # Ensure data directory exists
        self.data_dir = Path(".data")
        self.data_dir.mkdir(exist_ok=True)
        
        logger.info(f"Initialized scraper with base_url: {self.base_url}")
        logger.info(f"Max workers: {self.max_workers}, Total pages: {self.total_pages}")

    def get_session(self) -> requests.Session:
        """Get or create a session for the current thread"""
        if not hasattr(self.local_data, 'session'):
            session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET"]
            )
            
            # Mount adapter with retry strategy
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=20,
                pool_maxsize=20
            )
            
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Set headers
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            self.local_data.session = session
            
        return self.local_data.session

    def scrape_product_links(self, output_file: str = ".data/product_links.txt") -> List[str]:
        """Scrape product links from category pages"""
        logger.info("Starting to scrape product links from category pages")
        all_links = set()
        
        for page in range(1, self.total_pages + 1):
            url = f"{self.category_url}{page}"
            logger.info(f"Scraping page {page}/{self.total_pages}: {url}")
            
            try:
                response = requests.get(url, timeout=self.timeout)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page {page}, status code: {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                product_divs = soup.find_all("div", class_="urun")

                for div in product_divs:
                    a_tag = div.find("a", href=True)
                    if a_tag and a_tag["href"].startswith("urun/"):
                        full_link = self.base_url + "/" + a_tag["href"].lstrip("/")
                        all_links.add(full_link)
                        
                # Add small delay between pages
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error scraping page {page}: {e}")
                continue

        # Convert to sorted list
        links_list = sorted(list(all_links))
        
        # Save to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for link in links_list:
                    f.write(link + "\n")
            logger.info(f"✅ Saved {len(links_list)} product links to {output_file}")
        except Exception as e:
            logger.error(f"Error saving links to file: {e}")
        
        return links_list

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a single page with optimized session handling"""
        session = self.get_session()
        
        try:
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def clean_price(self, price_str: str) -> str:
        """Clean and normalize price strings"""
        if not price_str:
            return ""
        
        price_str = price_str.strip()
        if "TL" in price_str:
            numeric_matches = re.findall(r'[\d.,]+', price_str)
            if numeric_matches:
                numeric_part = numeric_matches[0]
                if ',' in numeric_part and '.' in numeric_part:
                    numeric_part = numeric_part.replace('.', '').replace(',', '.')
                elif ',' in numeric_part:
                    numeric_part = numeric_part.replace(',', '.')
                return f"{numeric_part} TRY"
        return price_str

    def parse_product_from_html(self, html_content: str, page_url: str = None) -> Optional[ProductInfo]:
        """Parse product information from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            base_url = self.base_url
            
            if base_url:
                parsed_url = urlparse(base_url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            product = ProductInfo()

            # ID
            if page_url:
                id_match = re.search(r'-(\d+)$', page_url)
                product.id = id_match.group(1) if id_match else page_url.split('/')[-1]

            # Title
            title_element = soup.find('h1')
            product.title = title_element.get_text(strip=True) if title_element else ""

            # Description
            description_div = soup.find('div', {'data-utabic': '1'})
            if description_div:
                desc_text = description_div.get_text(strip=True)
                product.description = desc_text[:5000]

            # Link
            product.link = page_url or ""

            # Images
            main_image = ""
            additional_images = []
            carousel_wrapper = soup.select_one('#sync1')
            if carousel_wrapper:
                carousel_items = carousel_wrapper.select('div.item > img.img-responsive')
                
                for i, img in enumerate(carousel_items):
                    if img and img.get('src'):
                        img_src = urljoin(base_url, img['src'])
                        if i == 0:
                            main_image = img_src
                        else:
                            additional_images.append(img_src)

            product.image_link = main_image
            product.additional_image_link = ','.join(additional_images[:10])

            # Availability
            stock_status = soup.find('span', string='Stok Durumu :')
            if stock_status and stock_status.find_next('strong'):
                status = stock_status.find_next('strong').get_text(strip=True).lower()
                product.availability = 'in stock' if 'mevcut' in status or 'stokta' in status else 'out of stock'
            else:
                product.availability = 'in stock'

            # Price and Sale Price
            price_div = soup.find('div', class_='yeni_fiyat')
            old_price_div = soup.find('div', class_='eski_fiyat')
            
            if price_div:
                price_span = price_div.select_one('div.col-md-8 > span')
                if price_span:
                    product.price = self.clean_price(price_span.get_text(strip=True))
            
            if old_price_div:
                old_price_span = old_price_div.select_one('div.col-md-8 > span')
                if old_price_span:
                    product.sale_price = product.price
                    product.price = self.clean_price(old_price_span.get_text(strip=True))

            # Condition
            product.condition = 'new'

            # Brand
            brand_div = soup.find('div', class_='marka')
            brand = ""
            if brand_div:
                brand_img = brand_div.find('img')
                if brand_img:
                    brand = brand_img.get('alt', '')
            
            if not brand and product.title:
                brand = product.title.split()[0]
            product.brand = brand

            # MPN
            stock_code = soup.find('span', string='Stok Kodu :')
            if stock_code and stock_code.find_next('strong'):
                product.mpn = stock_code.find_next('strong').get_text(strip=True)

            # GTIN
            product.gtin = ""

            # Category
            product.google_product_category = "Apparel & Accessories > Clothing Accessories > Sunglasses"

            # Adult
            product.adult = 'no'

            # Gender
            title_lower = product.title.lower()
            if 'erkek' in title_lower:
                product.gender = 'male'
            elif 'kadın' in title_lower:
                product.gender = 'female'
            elif 'unisex' in title_lower:
                product.gender = 'unisex'
            else:
                product.gender = 'unisex'

            product.age_group = 'adult'

            return product
            
        except Exception as e:
            logger.error(f"Error parsing product from {page_url}: {e}")
            return None

    def scrape_single_product(self, url: str) -> Optional[ProductInfo]:
        """Scrape a single product URL"""
        try:
            html = self.fetch_page(url)
            if html:
                product = self.parse_product_from_html(html, url)
                if product:
                    with self.progress_lock:
                        self.scraped_count += 1
                        logger.info(f"Scraped {self.scraped_count}/{self.total_count}: {url}")
                    return product
            
            # Add to failed URLs for potential retry
            self.failed_urls.put(url)
            return None
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            self.failed_urls.put(url)
            return None

    def retry_failed_urls(self, max_retries: int = 2) -> List[ProductInfo]:
        """Retry failed URLs with exponential backoff"""
        retry_results = []
        
        for retry_attempt in range(max_retries):
            if self.failed_urls.empty():
                break
                
            logger.info(f"Retry attempt {retry_attempt + 1}/{max_retries}")
            current_failed = []
            
            # Get all failed URLs
            while not self.failed_urls.empty():
                current_failed.append(self.failed_urls.get())
            
            if not current_failed:
                break
                
            # Retry with exponential backoff
            time.sleep(2 ** retry_attempt)
            
            with ThreadPoolExecutor(max_workers=min(5, self.max_workers)) as executor:
                future_to_url = {executor.submit(self.scrape_single_product, url): url 
                               for url in current_failed}
                
                for future in as_completed(future_to_url):
                    result = future.result()
                    if result:
                        retry_results.append(result)
        
        return retry_results

    def scrape_products_from_links(self, links: List[str], delay: float = 0.5, enable_retry: bool = True) -> None:
        """Scrape products from a list of links"""
        if not links:
            logger.error("No valid URLs provided")
            return

        self.total_count = len(links)
        self.scraped_count = 0
        
        logger.info(f"Starting to scrape {len(links)} product URLs with {self.max_workers} workers")
        
        start_time = time.time()
        
        # Main scraping with threading
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Add delay between submissions to avoid overwhelming the server
            futures = []
            for i, url in enumerate(links):
                future = executor.submit(self.scrape_single_product, url)
                futures.append(future)
                
                # Add delay between submissions
                if i < len(links) - 1:
                    time.sleep(delay)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                if result:
                    with self.results_lock:
                        self.results.append(result)

        # Retry failed URLs if enabled
        if enable_retry:
            retry_results = self.retry_failed_urls()
            self.results.extend(retry_results)

        end_time = time.time()
        logger.info(f"Product scraping completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Successfully scraped {len(self.results)} products")
        
        if not self.failed_urls.empty():
            failed_count = self.failed_urls.qsize()
            logger.warning(f"{failed_count} URLs failed after retries")

    def write_results_to_tsv(self, output_file: str) -> None:
        """Write results to TSV file"""
        if not self.results:
            logger.warning("No results to write")
            return
            
        headers = [
            'id', 'title', 'description', 'link', 'image_link', 'additional_image_link',
            'availability', 'price', 'sale_price', 'brand', 'mpn', 'gtin',
            'google_product_category', 'condition', 'adult', 'gender', 'age_group'
        ]

        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                
                for product in self.results:
                    row = asdict(product)
                    writer.writerow(row)
            
            logger.info(f"Successfully exported {len(self.results)} products to {output_file}")
            
        except Exception as e:
            logger.error(f"Error writing TSV file: {e}")

    def export_to_json(self, output_file: str) -> None:
        """Export results to JSON format"""
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(product) for product in self.results], f, 
                         indent=2, ensure_ascii=False)
            logger.info(f"Successfully exported to JSON: {output_file}")
        except Exception as e:
            logger.error(f"Error writing JSON file: {e}")

    def upload_to_sftp(self, local_file_path: str, remote_file_name: str = None) -> bool:
        """Upload file to Google Merchant Center SFTP server"""
        if not remote_file_name:
            remote_file_name = os.path.basename(local_file_path)
        
        # SFTP connection parameters
        # Load SFTP credentials from environment variables
        sftp_host = os.getenv('SFTP_HOST', 'partnerupload.google.com')
        sftp_port = int(os.getenv('SFTP_PORT', '19321'))
        sftp_username = os.getenv('SFTP_USERNAME')
        sftp_password = os.getenv('SFTP_PASSWORD')
        
        # Check if credentials are provided
        if not sftp_username or not sftp_password:
            logger.error("SFTP credentials not found in environment variables")
            return False
        
        try:
            logger.info(f"Connecting to SFTP server: {sftp_host}:{sftp_port}")
            
            # Create SSH client
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to SFTP server
            ssh_client.connect(
                hostname=sftp_host,
                port=sftp_port,
                username=sftp_username,
                password=sftp_password,
                timeout=30
            )
            
            # Create SFTP client
            sftp_client = ssh_client.open_sftp()
            
            # Upload file
            logger.info(f"Uploading {local_file_path} to {remote_file_name}")
            sftp_client.put(local_file_path, remote_file_name)
            
            # Close connections
            sftp_client.close()
            ssh_client.close()
            
            logger.info(f"✅ Successfully uploaded {local_file_path} to SFTP server")
            return True
            
        except paramiko.AuthenticationException:
            logger.error("❌ SFTP authentication failed - check username/password")
            return False
        except paramiko.SSHException as e:
            logger.error(f"❌ SFTP SSH error: {e}")
            return False
        except FileNotFoundError:
            logger.error(f"❌ Local file not found: {local_file_path}")
            return False
        except Exception as e:
            logger.error(f"❌ SFTP upload error: {e}")
            return False

    def get_statistics(self) -> Dict:
        """Get scraping statistics"""
        stats = {
            'total_urls': self.total_count,
            'successful_scrapes': len(self.results),
            'failed_scrapes': self.failed_urls.qsize(),
            'success_rate': (len(self.results) / self.total_count * 100) if self.total_count > 0 else 0
        }
        return stats

    def run_complete_scraping(self, scrape_links: bool = True, links_file: str = ".data/product_links.txt", 
                             tsv_output: str = ".data/google_merchant_products.tsv",
                             json_output: str = ".data/google_merchant_products.json",
                             delay: float = 0.5, enable_retry: bool = True, 
                             upload_to_sftp: bool = True) -> None:
        """Run the complete scraping process"""
        logger.info("🚀 Starting complete scraping process")
        overall_start_time = time.time()
        
        # Step 1: Scrape product links if requested
        if scrape_links:
            logger.info("📋 Step 1: Scraping product links from category pages")
            links = self.scrape_product_links(links_file)
        else:
            logger.info("📋 Step 1: Loading existing links from file")
            try:
                with open(links_file, 'r', encoding='utf-8') as f:
                    links = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                logger.info(f"Loaded {len(links)} links from {links_file}")
            except FileNotFoundError:
                logger.error(f"Links file {links_file} not found. Set scrape_links=True to create it.")
                return
            except Exception as e:
                logger.error(f"Error reading links file: {e}")
                return
        
        if not links:
            logger.error("No links found to scrape")
            return
        
        # Step 2: Scrape product details
        logger.info("🛍️ Step 2: Scraping product details")
        self.scrape_products_from_links(links, delay, enable_retry)
        
        # Step 3: Export results
        logger.info("💾 Step 3: Exporting results")
        self.write_results_to_tsv(tsv_output)
        self.export_to_json(json_output)
        
        # Step 4: Upload to SFTP if requested
        if upload_to_sftp:
            logger.info("📤 Step 4: Uploading TSV file to Google Merchant Center SFTP")
            upload_success = self.upload_to_sftp(tsv_output)
            if not upload_success:
                logger.warning("SFTP upload failed, but local files are available")
        
        # Step 5: Show statistics
        overall_end_time = time.time()
        stats = self.get_statistics()
        
        logger.info("📊 SCRAPING COMPLETE!")
        logger.info(f"⏱️ Total time: {overall_end_time - overall_start_time:.2f} seconds")
        logger.info(f"🔗 Total links found: {len(links)}")
        logger.info(f"✅ Successfully scraped: {stats['successful_scrapes']} products")
        logger.info(f"❌ Failed: {stats['failed_scrapes']} products")
        logger.info(f"📈 Success rate: {stats['success_rate']:.1f}%")
        logger.info(f"📁 TSV output: {tsv_output}")
        logger.info(f"📁 JSON output: {json_output}")
        if upload_to_sftp:
            logger.info("📤 TSV file uploaded to Google Merchant Center SFTP")

def main():
    """Main function with configuration options"""
    try:
        logger.info("🚀 Starting Utku Optik Scraper")
        
        # Get configuration from environment variables
        scrape_links = os.getenv('SCRAPE_LINKS', 'true').lower() == 'true'
        max_workers = int(os.getenv('MAX_WORKERS', '8'))
        delay = float(os.getenv('DELAY', '0.1'))
        enable_retry = os.getenv('ENABLE_RETRY', 'true').lower() == 'true'
        upload_to_sftp = os.getenv('UPLOAD_TO_SFTP', 'true').lower() == 'true'
        
        scraper = CombinedUtkuOptikScraper(
            max_workers=max_workers,
            timeout=15
        )
        
        # Run the complete scraping process
        scraper.run_complete_scraping(
            scrape_links=scrape_links,
            links_file=".data/product_links.txt",
            tsv_output=".data/google_merchant_products.tsv",
            json_output=".data/google_merchant_products.json",
            delay=delay,
            enable_retry=enable_retry,
            upload_to_sftp=upload_to_sftp
        )
        
        logger.info("✅ Scraping completed successfully")
        
    except KeyboardInterrupt:
        logger.info("❌ Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error during scraping: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
