#!/usr/bin/env python3
"""
Master Health News Scraper - Unified Scraper

This unified scraper combines all health news sources into a single, efficient scraper:
- RSS feeds from WHO, NIH, WebMD, Mayo Clinic
- Google News health searches
- Major news outlets (Reuters, CNN, BBC)
- Health-specific sources
- International health news

Replaces: comprehensive_news_scraper.py, simple_health_scraper.py, 
python313_compatible_scraper.py, lifestyle_scraper.py, comprehensive_category_scraper.py,
enhanced_international_scraper.py
"""

import sys
from pathlib import Path
import requests
import sqlite3
import json
import re
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, quote_plus

# Handle Python 3.13 compatibility
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError as e:
    if "cgi" in str(e):
        print("⚠️ Python 3.13 detected - feedparser not compatible, using fallback")
        FEEDPARSER_AVAILABLE = False
    else:
        raise e

from bs4 import BeautifulSoup

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Import our URL validator and categorizer
try:
    sys.path.insert(0, str(BASE_DIR))
    from app.url_validator import URLValidator
    from app.categorizer import health_categorizer
except ImportError:
    class URLValidator:
        def validate_article_url(self, article):
            return True, {"status": "valid"}
    
    # Fallback categorizer if import fails
    class FallbackCategorizer:
        def categorize_article(self, title, summary, source_category=None):
            return "news", "general"
    
    health_categorizer = FallbackCategorizer()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = BASE_DIR / "data" / "articles.db"

class MasterHealthScraper:
    """Unified health news scraper combining all sources"""
    
    def __init__(self):
        self.url_validator = URLValidator()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        # Health keywords for searches
        self.health_keywords = [
            "metabolic health", "diabetes", "nutrition", "diet", "fitness", "wellness",
            "mental health", "heart disease", "obesity", "lifestyle", "exercise",
            "public health", "food safety", "sleep disorder", "immunity", "preventive care"
        ]
        
        # Unified RSS sources - Optimized list (verified working URLs)
        self.rss_sources = [
            # Major News Outlets - Health Sections (Verified Working)
            {"name": "BBC Health", "url": "http://feeds.bbci.co.uk/news/health/rss.xml", "category": "health_news"},
            {"name": "The Hindu Health", "url": "https://www.thehindu.com/sci-tech/health/feeder/default.rss", "category": "health_news"},
            {"name": "CNN Health", "url": "http://rss.cnn.com/rss/edition.rss", "category": "health_news"},
            {"name": "NPR Health", "url": "https://feeds.npr.org/1001/rss.xml", "category": "health_news"},
            
            # Medical and Health Information Sources - Fast loading
            {"name": "Medical News Today", "url": "https://www.medicalnewstoday.com/rss", "category": "health_info"},
            {"name": "Healthline News", "url": "https://www.healthline.com/rss", "category": "health_info"},
            {"name": "Medical Xpress", "url": "https://medicalxpress.com/rss-feed/", "category": "medical_research"},
            {"name": "ScienceDaily Health", "url": "https://www.sciencedaily.com/rss/health_medicine.xml", "category": "medical_research"},
            
            # Government sources (verified working)
            {"name": "NIH News Releases", "url": "https://www.nih.gov/news-events/news-releases/feed", "category": "medical_research"},
        ]

    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    summary TEXT,
                    url TEXT UNIQUE NOT NULL,
                    categories TEXT,
                    tags TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    priority INTEGER DEFAULT 1,
                    url_health TEXT,
                    url_accessible INTEGER DEFAULT 1,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subcategory TEXT,
                    news_score REAL DEFAULT 0.0,
                    trending_score REAL DEFAULT 0.0,
                    content_quality_score REAL DEFAULT 0.0
                )
            """)
            conn.commit()

    def scrape_rss_source(self, source: Dict) -> List[Dict]:
        """Scrape a single RSS source with enhanced error handling and performance optimization"""
        articles = []
        try:
            logger.info(f"Scraping {source['name']}...")
            
            # Try feedparser first (if available) with timeout
            if FEEDPARSER_AVAILABLE:
                try:
                    # Set socket timeout for feedparser
                    import socket
                    old_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(15)
                    
                    feed = feedparser.parse(source['url'])
                    
                    # Restore original timeout
                    socket.setdefaulttimeout(old_timeout)
                    
                    if not feed.entries:
                        raise Exception("No entries found")
                        
                    for entry in feed.entries[:15]:  # Reduced to 15 articles per source for speed
                        article = self._parse_rss_entry(entry, source)
                        if article:
                            articles.append(article)
                            
                except Exception as e:
                    logger.debug(f"Feedparser failed for {source['name']}: {e}, trying manual parsing")
                    articles.extend(self._manual_rss_parse(source))
            else:
                # Use manual parsing when feedparser is not available (Python 3.13)
                logger.info(f"Using manual RSS parsing for {source['name']} (Python 3.13 compatibility)")
                articles.extend(self._manual_rss_parse(source))
                
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "403" in error_msg or "Not Found" in error_msg or "Forbidden" in error_msg:
                logger.warning(f"⚠️ {source['name']} feed is currently unavailable (will retry next scrape): {error_msg}")
            elif "Name or service not known" in error_msg or "Failed to resolve" in error_msg:
                logger.warning(f"⚠️ Network issue accessing {source['name']} (will retry next scrape): DNS resolution failed")
            else:
                logger.error(f"❌ Failed to scrape {source['name']}: {e}")
        
        if articles:
            logger.info(f"✅ Successfully scraped {len(articles)} articles from {source['name']}")
        else:
            logger.warning(f"⚠️ No articles found for {source['name']} (source may be temporarily unavailable)")
            
        return articles

    def _parse_rss_entry(self, entry, source: Dict) -> Optional[Dict]:
        """Parse individual RSS entry"""
        try:
            # Extract basic info
            title = getattr(entry, 'title', '').strip()
            description = getattr(entry, 'summary', '').strip()
            url = getattr(entry, 'link', '').strip()
            
            if not title or not url:
                return None
            
            # Parse date
            published_date = self._parse_date(getattr(entry, 'published', ''))
            
            # Get image URL
            image_url = self._extract_image_from_entry(entry)
            
            # Use intelligent categorizer to get main category and subcategory
            main_category, subcategory = health_categorizer.categorize_article(
                title, 
                self._clean_html(description), 
                source['category']
            )
            
            # Create article object
            article = {
                'title': title,
                'summary': self._clean_html(description)[:500],  # Changed from 'description' to 'summary'
                'url': url,
                'published_date': published_date,
                'source': source['name'],
                'category': main_category,  # Use intelligent categorization
                'subcategory': subcategory,  # Add subcategory
                'tags': self._generate_tags(title, description, source['category']),
                'image_url': image_url,
                'author': getattr(entry, 'author', ''),
                'read_time': max(3, len(description.split()) // 200)  # Estimate read time
            }
            
            # Quick URL validation (avoid slow HTTP requests during scraping)
            is_valid, validation_info = self._quick_url_validation(article)
            if not is_valid:
                logger.debug(f"Skipping article with invalid URL: {url} - {validation_info.get('error', 'Unknown error')}")
                return None
                
            return article
            
        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            return None

    def _manual_rss_parse(self, source: Dict) -> List[Dict]:
        """Manual RSS parsing for sources where feedparser fails - Enhanced"""
        articles = []
        try:
            # Add timeout and better headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml, text/xml',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = self.session.get(source['url'], timeout=30, headers=headers)
            response.raise_for_status()
            
            # Simple XML parsing for basic RSS structure
            content = response.text
            
            # Extract items using regex (basic approach)
            item_pattern = r'<item>(.*?)</item>'
            items = re.findall(item_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if not items:
                # Try alternative RSS structures
                item_pattern = r'<entry>(.*?)</entry>'
                items = re.findall(item_pattern, content, re.DOTALL | re.IGNORECASE)
            
            for item in items[:15]:  # Reduced to 15 articles for speed
                title_match = re.search(r'<title[^>]*>(.*?)</title>', item, re.DOTALL | re.IGNORECASE)
                link_match = re.search(r'<link[^>]*>(.*?)</link>', item, re.DOTALL | re.IGNORECASE)
                desc_match = re.search(r'<description[^>]*>(.*?)</description>', item, re.DOTALL | re.IGNORECASE)
                date_match = re.search(r'<pubDate[^>]*>(.*?)</pubDate>', item, re.DOTALL | re.IGNORECASE)
                
                # Try alternative date fields
                if not date_match:
                    date_match = re.search(r'<published[^>]*>(.*?)</published>', item, re.DOTALL | re.IGNORECASE)
                if not date_match:
                    date_match = re.search(r'<updated[^>]*>(.*?)</updated>', item, re.DOTALL | re.IGNORECASE)
                
                # Try alternative summary fields if description not found
                if not desc_match:
                    desc_match = re.search(r'<summary[^>]*>(.*?)</summary>', item, re.DOTALL | re.IGNORECASE)
                if not desc_match:
                    desc_match = re.search(r'<content[^>]*>(.*?)</content>', item, re.DOTALL | re.IGNORECASE)
                
                if title_match and link_match:
                    title = self._clean_html(title_match.group(1).strip())
                    url = link_match.group(1).strip()
                    description = self._clean_html(desc_match.group(1).strip()) if desc_match else ""
                    pub_date = self._parse_date(date_match.group(1).strip()) if date_match else datetime.now().isoformat()
                    
                    if title and url:
                        # Use intelligent categorizer to get main category and subcategory
                        main_category, subcategory = health_categorizer.categorize_article(
                            title, 
                            description, 
                            source['category']
                        )
                        
                        article = {
                            'title': title,
                            'summary': description[:500],
                            'url': url,
                            'published_date': pub_date,
                            'source': source['name'],
                            'category': main_category,  # Use intelligent categorization
                            'subcategory': subcategory,  # Add subcategory
                            'tags': self._generate_tags(title, description, source['category']),
                            'image_url': '',
                            'author': '',
                            'read_time': max(3, len(description.split()) // 200)
                        }
                        
                        # Quick URL validation (avoid slow HTTP requests during scraping)
                        is_valid, validation_info = self._quick_url_validation(article)
                        if is_valid:
                            articles.append(article)
                        else:
                            logger.debug(f"Skipping article with invalid URL in manual parse: {url} - {validation_info.get('error', 'Unknown error')}")
        
        except Exception as e:
            # Don't log as error - this is already a fallback method
            logger.debug(f"Manual parsing failed for {source['name']}: {e}")
        
        return articles

    def scrape_google_news(self) -> List[Dict]:
        """Scrape Google News for health topics"""
        articles = []
        
        # Skip Google News if feedparser is not available
        if not FEEDPARSER_AVAILABLE:
            logger.info("Skipping Google News scraping (feedparser not available in Python 3.13)")
            return articles
        
        for keyword in self.health_keywords[:5]:  # Reduced keywords for faster processing
            try:
                url = f"https://news.google.com/rss/search?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
                
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:  # 5 articles per keyword
                    article = self._parse_rss_entry(entry, {
                        'name': 'Google News',
                        'category': 'health_news'
                    })
                    
                    if article:
                        article['tags'] = f"{article['tags']},{keyword}" if article['tags'] else keyword
                        
                        # Quick URL validation for Google News articles
                        is_valid, validation_info = self._quick_url_validation(article)
                        if is_valid:
                            articles.append(article)
                        else:
                            logger.debug(f"Skipping Google News article with invalid URL: {article.get('url')} - {validation_info.get('error', 'Unknown error')}")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Failed to scrape Google News for '{keyword}': {e}")
        
        return articles

    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats to ISO format"""
        if not date_str:
            return datetime.now().isoformat()
        
        # Common date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %Z',
            '%a, %d %b %Y %H:%M:%S %z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).isoformat()
            except:
                continue
        
        return datetime.now().isoformat()

    def _clean_html(self, text: str) -> str:
        """Clean HTML tags and entities from text"""
        if not text:
            return ""
        
        # Remove CDATA sections
        if text.startswith('<![CDATA[') and text.endswith(']]>'):
            text = text[9:-3]
        
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Replace HTML entities
        clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        clean = clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        
        return clean.strip()

    def _extract_image_from_entry(self, entry) -> str:
        """Extract image URL from RSS entry"""
        # Try various common image fields
        if hasattr(entry, 'media_content') and entry.media_content:
            return entry.media_content[0].get('url', '')
        
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type and 'image' in enclosure.type:
                    return enclosure.href
        
        # Look for images in description
        if hasattr(entry, 'summary'):
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.summary)
            if img_match:
                return img_match.group(1)
        
        return ""

    def _quick_url_validation(self, article: Dict) -> Tuple[bool, Dict]:
        """
        Quick URL validation without HTTP requests (for performance during scraping)
        Only checks URL format and domain patterns - detailed validation can be done later
        """
        url = article.get('url', '')
        
        if not url:
            return False, {"error": "No URL provided", "status": "invalid"}
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Basic URL structure validation
            if not parsed.scheme or not parsed.netloc:
                return False, {"error": "Invalid URL format", "status": "invalid"}
            
            # Check for problematic domains and patterns
            domain = parsed.netloc.lower()
            
            # Reject example domains and test domains
            invalid_domains = [
                'example.com', 'example.org', 'example.net',
                'test.com', 'test.org', 'localhost',
                'domain.com', 'sample.com', 'dummy.com'
            ]
            
            for invalid_domain in invalid_domains:
                if invalid_domain in domain:
                    return False, {"error": f"Invalid domain: {domain}", "status": "invalid"}
            
            # Reject problematic URL patterns
            invalid_patterns = [
                'javascript:', 'mailto:', 'file:', 'ftp:',
                '/404', '/error', '/not-found',
                '?error=', '&error=', '#error'
            ]
            
            for pattern in invalid_patterns:
                if pattern in url.lower():
                    return False, {"error": f"Invalid URL pattern: {pattern}", "status": "invalid"}
            
            # Accept if it looks like a legitimate news URL
            return True, {"status": "valid_format"}
            
        except Exception as e:
            return False, {"error": f"URL parsing failed: {e}", "status": "invalid"}

    def _generate_tags(self, title: str, description: str, category: str) -> str:
        """Generate relevant tags for the article"""
        tags = [category]
        
        text = f"{title} {description}".lower()
        
        # Health-related tag mapping
        tag_keywords = {
            'diabetes': ['diabetes', 'blood sugar', 'insulin', 'glucose'],
            'nutrition': ['nutrition', 'diet', 'food', 'eating', 'vitamin'],
            'fitness': ['fitness', 'exercise', 'workout', 'physical activity'],
            'mental_health': ['mental health', 'depression', 'anxiety', 'stress'],
            'heart_health': ['heart', 'cardiovascular', 'blood pressure', 'cholesterol'],
            'weight_management': ['weight', 'obesity', 'overweight', 'BMI'],
            'preventive_care': ['prevention', 'screening', 'early detection'],
            'lifestyle': ['lifestyle', 'wellness', 'healthy living'],
            'women_health': ['women', 'pregnancy', 'maternal'],
            'men_health': ['men', 'prostate', 'testosterone'],
            'elderly': ['elderly', 'aging', 'senior']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        
        return ','.join(list(set(tags)))  # Remove duplicates

    def save_articles(self, articles: List[Dict]) -> int:
        """Save articles to database"""
        saved_count = 0
        
        with sqlite3.connect(DB_PATH) as conn:
            for article in articles:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO articles 
                        (title, summary, url, date, source, categories, subcategory, tags, url_health, authors)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        article['title'],
                        article['summary'],  # Changed from 'description' to 'summary'
                        article['url'],
                        article['published_date'],  # Maps to 'date' column
                        article['source'],
                        article['category'],  # Maps to 'categories' column
                        article.get('subcategory', ''),  # Add subcategory
                        article['tags'],
                        article.get('image_url', ''),  # Maps to 'url_health' column for images
                        article.get('author', '')  # Maps to 'authors' column
                    ))
                    
                    if conn.total_changes > 0:
                        saved_count += 1
                        
                except Exception as e:
                    logger.error(f"Error saving article '{article['title']}': {e}")
            
            conn.commit()
        
        return saved_count

    def run_scraping(self) -> Dict:
        """Run complete scraping process"""
        logger.info("🚀 Starting Master Health Scraper...")
        
        # Initialize database
        self.init_database()
        
        all_articles = []
        
        # Scrape RSS sources (optimized for speed)
        for source in self.rss_sources:
            articles = self.scrape_rss_source(source)
            all_articles.extend(articles)
            time.sleep(0.5)  # Reduced delay for faster scraping
        
        # Scrape Google News
        google_articles = self.scrape_google_news()
        all_articles.extend(google_articles)
        
        # Save to database
        saved_count = self.save_articles(all_articles)
        
        result = {
            'total_scraped': len(all_articles),
            'total_saved': saved_count,
            'sources_processed': len(self.rss_sources) + 1,  # +1 for Google News
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Scraping completed: {saved_count}/{len(all_articles)} articles saved")
        return result

def main():
    """Main execution function"""
    scraper = MasterHealthScraper()
    result = scraper.run_scraping()
    
    print("\n" + "="*60)
    print("🏥 MASTER HEALTH SCRAPER - RESULTS")
    print("="*60)
    print(f"📊 Total Articles Scraped: {result['total_scraped']}")
    print(f"💾 Articles Saved to Database: {result['total_saved']}")
    print(f"🌐 Sources Processed: {result['sources_processed']}")
    print(f"⏰ Completed at: {result['timestamp']}")
    print("="*60)
    
    return result

if __name__ == "__main__":
    main()
