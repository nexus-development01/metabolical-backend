#!/usr/bin/env python3


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
    # cache_manager removed: always fetch fresh data
except ImportError:
    class URLValidator:
        def validate_article_url(self, article):
            return True, {"status": "valid"}
    
    # Fallback categorizer if import fails
    class FallbackCategorizer:
        def categorize_article(self, title, summary, source_category=None):
            return "news", "general"
    
    health_categorizer = FallbackCategorizer()
    
    # cache_manager removed: always fetch fresh data

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
        
        # Enhanced health keywords for comprehensive metabolic health coverage
        self.health_keywords = [
            # Core Metabolic Health Terms
            "metabolic health", "metabolic syndrome", "diabetes", "insulin resistance", "obesity",
            "type 2 diabetes", "prediabetes", "glucose metabolism", "lipid metabolism",
            
            # Nutrition & Food Science
            "nutrition", "diet", "processed foods", "ultra-processed foods", "sugar", "fructose",
            "artificial sweeteners", "glycemic index", "micronutrients", "gut microbiome",
            
            # Lifestyle & Prevention
            "fitness", "exercise", "physical activity", "weight management", "preventive care",
            "lifestyle medicine", "stress management", "sleep health", "circadian rhythm",
            
            # Environmental Health
            "endocrine disruptors", "air pollution", "water pollution", "pesticides", "heavy metals",
            "microplastics", "environmental toxins", "chemical exposure",
            
            # Agriculture & Food Systems
            "sustainable agriculture", "organic farming", "GMOs", "food security", "soil health",
            "agricultural chemicals", "food safety", "industrial farming",
            
            # Broader Health Topics
            "mental health", "cardiovascular health", "inflammation", "autoimmune", "hormone health",
            "thyroid health", "adrenal health", "women's health", "men's health"
        ]
        
        # Unified RSS sources - Comprehensive list covering metabolic health, nutrition, environment, and agriculture
        self.rss_sources = [
            # Major News Outlets - Health Sections (Verified Working)
            {"name": "BBC Health", "url": "http://feeds.bbci.co.uk/news/health/rss.xml", "category": "health_news"},
            {"name": "The Hindu Health", "url": "https://www.thehindu.com/sci-tech/health/feeder/default.rss", "category": "health_news"},
            {"name": "CNN Health", "url": "http://rss.cnn.com/rss/edition.rss", "category": "health_news"},
            {"name": "NPR Health", "url": "https://feeds.npr.org/1001/rss.xml", "category": "health_news"},
            
            # 🧬 Medical & Scientific News Sources - Metabolic Health Focus
            {"name": "Medical News Today", "url": "https://www.medicalnewstoday.com/rss", "category": "medical_research"},
            {"name": "Healthline News", "url": "https://www.healthline.com/rss", "category": "health_info"},
            {"name": "WebMD News", "url": "https://www.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC", "category": "health_info"},
            {"name": "Medical Xpress", "url": "https://medicalxpress.com/rss-feed/", "category": "medical_research"},
            {"name": "ScienceDaily Health", "url": "https://www.sciencedaily.com/rss/health_medicine.xml", "category": "medical_research"},
            {"name": "ScienceDaily Environmental Health", "url": "https://www.sciencedaily.com/rss/health_medicine/environmental_health.xml", "category": "environmental_health"},
            
            # Government & Authoritative Sources
            {"name": "NIH News Releases", "url": "https://www.nih.gov/news-events/news-releases/feed", "category": "medical_research"},
            {"name": "CDC Newsroom", "url": "https://tools.cdc.gov/api/v2/resources/media/316422.rss", "category": "public_health"},
            {"name": "WHO News", "url": "https://www.who.int/rss-feeds/news-english.xml", "category": "global_health"},
            
            # 🥗 Nutrition & Food Science Sources
            {"name": "Harvard Nutrition Source", "url": "https://www.hsph.harvard.edu/nutritionsource/feed/", "category": "nutrition_science"},
            {"name": "The Conversation Health", "url": "https://theconversation.com/global/health/articles.atom", "category": "health_education"},
            {"name": "Food Navigator", "url": "https://www.foodnavigator.com/rssfeed/latest", "category": "food_industry"},
            {"name": "Food Navigator USA", "url": "https://www.foodnavigator-usa.com/rssfeed/latest", "category": "food_industry"},
            
            # 🌾 Agriculture & Food Policy Sources
            {"name": "AgFunder News", "url": "https://agfundernews.com/feed/", "category": "agriculture_tech"},
            {"name": "Civil Eats", "url": "https://civileats.com/feed/", "category": "food_systems"},
            {"name": "FAO News", "url": "https://www.fao.org/news/rss-feed/en/", "category": "global_food_security"},
            
            # 🌫️ Environment & Pollution Sources
            {"name": "Environmental Health News", "url": "https://www.ehn.org/rss.xml", "category": "environmental_health"},
            {"name": "Inside Climate News", "url": "https://insideclimatenews.org/feed/", "category": "climate_health"},
            {"name": "National Geographic Environment", "url": "https://www.nationalgeographic.com/pages/topic/planet-possible/feed/", "category": "environmental_science"},
            
            # 💡 Academic & Research Aggregators
            {"name": "EurekAlert Health", "url": "https://www.eurekalert.org/rss/health_medicine.xml", "category": "academic_research"},
            {"name": "EurekAlert Environment", "url": "https://www.eurekalert.org/rss/environment.xml", "category": "environmental_research"},
            {"name": "Reuters Health", "url": "https://www.reuters.com/rss/healthNews", "category": "health_news"},
            
            # Specialized Metabolic Health Sources
            {"name": "Diabetes Research News", "url": "https://www.sciencedaily.com/rss/health_medicine/diabetes.xml", "category": "diabetes_research"},
            {"name": "Obesity Research News", "url": "https://www.sciencedaily.com/rss/health_medicine/obesity.xml", "category": "obesity_research"},
            {"name": "Nutrition Research News", "url": "https://www.sciencedaily.com/rss/health_medicine/nutrition.xml", "category": "nutrition_research"},
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

    def scrape_pubmed_feeds(self) -> List[Dict]:
        """Scrape PubMed RSS feeds for latest research"""
        articles = []
        
        # Skip PubMed if feedparser is not available
        if not FEEDPARSER_AVAILABLE:
            logger.info("Skipping PubMed scraping (feedparser not available in Python 3.13)")
            return articles
        
        # PubMed RSS feeds for specific metabolic health topics
        pubmed_feeds = [
            {
                "name": "PubMed Metabolic Syndrome",
                "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1KXlwj8Ls4zOSKM-U0RNHwm3QwB5UHWGCJ6aBZBmQ",
                "category": "academic_research"
            },
            {
                "name": "PubMed Diabetes Research", 
                "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1qGz5uaLs4zPTKN-V1SMIxn4RxC6VIGDDK7bCaDnR",
                "category": "academic_research"
            },
            {
                "name": "PubMed Obesity Research",
                "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1rHz6vbMs5zQULO-W2TNJyo5SyD7WJHEEL8cDbEoS",
                "category": "academic_research"
            }
        ]
        
        for feed_info in pubmed_feeds:
            try:
                logger.info(f"Scraping {feed_info['name']}...")
                
                # Use a more permissive timeout for academic sources
                import socket
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(20)
                
                feed = feedparser.parse(feed_info['url'])
                
                # Restore original timeout
                socket.setdefaulttimeout(old_timeout)
                
                for entry in feed.entries[:10]:  # 10 research articles per feed
                    article = self._parse_rss_entry(entry, feed_info)
                    if article:
                        # Mark as academic research
                        article['tags'] = f"{article['tags']},academic research,pubmed" if article['tags'] else "academic research,pubmed"
                        articles.append(article)
                
                time.sleep(2)  # Respectful rate limiting for academic sources
                
            except Exception as e:
                logger.debug(f"PubMed feed {feed_info['name']} unavailable: {e}")
        
        if articles:
            logger.info(f"✅ PubMed: Found {len(articles)} research articles")
        return articles

    def scrape_google_news(self) -> List[Dict]:
        """Scrape Google News for health topics with enhanced metabolic health focus"""
        articles = []
        
        # Skip Google News if feedparser is not available
        if not FEEDPARSER_AVAILABLE:
            logger.info("Skipping Google News scraping (feedparser not available in Python 3.13)")
            return articles
        
        # Priority keywords for metabolic health
        priority_keywords = [
            "metabolic syndrome", "insulin resistance", "type 2 diabetes", 
            "obesity epidemic", "processed foods", "gut microbiome",
            "endocrine disruptors", "food security", "sustainable agriculture"
        ]
        
        # Use priority keywords first, then general health keywords
        search_keywords = priority_keywords + self.health_keywords[:8]  # Increased to 8 for better coverage
        
        for keyword in search_keywords[:12]:  # Process up to 12 keywords total
            try:
                url = f"https://news.google.com/rss/search?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
                
                feed = feedparser.parse(url)
                for entry in feed.entries[:4]:  # 4 articles per keyword for balance
                    article = self._parse_rss_entry(entry, {
                        'name': 'Google News',
                        'category': 'health_news'
                    })
                    
                    if article:
                        # Add the search keyword as a tag
                        existing_tags = article.get('tags', '')
                        if existing_tags:
                            article['tags'] = f"{existing_tags},{keyword}"
                        else:
                            article['tags'] = keyword
                        
                        # Quick URL validation for Google News articles
                        is_valid, validation_info = self._quick_url_validation(article)
                        if is_valid:
                            articles.append(article)
                        else:
                            logger.debug(f"Skipping Google News article with invalid URL: {article.get('url')} - {validation_info.get('error', 'Unknown error')}")
                
                time.sleep(1.5)  # Slightly increased rate limiting for respectful scraping
                
            except Exception as e:
                logger.error(f"Failed to scrape Google News for '{keyword}': {e}")
        
        logger.info(f"✅ Google News: Found {len(articles)} articles from {len(search_keywords)} keyword searches")
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
        """Generate relevant tags for the article with enhanced metabolic health focus"""
        tags = [category]
        
        text = f"{title} {description}".lower()
        
        # Enhanced health-related tag mapping for metabolic health focus
        tag_keywords = {
            # Metabolic Health Core
            'diabetes': ['diabetes', 'diabetic', 'blood sugar', 'insulin', 'glucose', 'a1c', 'glycemic'],
            'obesity': ['obesity', 'obese', 'overweight', 'weight loss', 'bariatric', 'bmi', 'adipose'],
            'metabolic_syndrome': ['metabolic syndrome', 'insulin resistance', 'cardiometabolic', 'syndrome x'],
            'hypertension': ['hypertension', 'blood pressure', 'high blood pressure', 'systolic', 'diastolic'],
            'hyperlipidemia': ['cholesterol', 'triglycerides', 'ldl', 'hdl', 'lipids', 'dyslipidemia'],
            
            # Nutrition & Diet
            'nutrition': ['nutrition', 'nutritional', 'diet', 'dietary', 'food', 'eating', 'meal'],
            'processed_foods': ['processed food', 'ultra-processed', 'packaged food', 'junk food', 'fast food'],
            'sugar': ['sugar', 'fructose', 'glucose', 'sweetener', 'high fructose corn syrup', 'sucrose'],
            'micronutrients': ['vitamin', 'mineral', 'micronutrient', 'deficiency', 'supplement'],
            'gut_health': ['gut', 'microbiome', 'probiotic', 'prebiotic', 'digestive', 'intestinal'],
            
            # Lifestyle & Prevention
            'fitness': ['fitness', 'exercise', 'workout', 'physical activity', 'training', 'gym'],
            'weight_management': ['weight management', 'weight loss', 'weight gain', 'calorie', 'portion'],
            'preventive_care': ['prevention', 'preventive', 'screening', 'early detection', 'checkup'],
            'lifestyle': ['lifestyle', 'wellness', 'healthy living', 'behavior', 'habit'],
            'sleep': ['sleep', 'insomnia', 'sleep quality', 'circadian', 'melatonin', 'rest'],
            
            # Environmental Health
            'environmental_toxins': ['pollution', 'toxin', 'chemical', 'pesticide', 'herbicide', 'contamination'],
            'endocrine_disruptors': ['endocrine disruptor', 'hormone disruptor', 'bpa', 'phthalate'],
            'air_pollution': ['air pollution', 'smog', 'particulate matter', 'pm2.5', 'ozone'],
            'water_pollution': ['water pollution', 'contaminated water', 'heavy metal', 'microplastic'],
            
            # Agriculture & Food Systems
            'organic_farming': ['organic', 'organic farming', 'sustainable agriculture', 'pesticide-free'],
            'gmos': ['gmo', 'genetically modified', 'genetic engineering', 'bioengineered'],
            'food_security': ['food security', 'food insecurity', 'hunger', 'malnutrition'],
            'soil_health': ['soil', 'soil health', 'soil degradation', 'erosion', 'topsoil'],
            
            # Broader Health Categories
            'mental_health': ['mental health', 'depression', 'anxiety', 'stress', 'mood', 'psychological'],
            'heart_health': ['heart', 'cardiac', 'cardiovascular', 'coronary', 'angina', 'stroke'],
            'inflammation': ['inflammation', 'inflammatory', 'chronic inflammation', 'immune response'],
            'hormone_health': ['hormone', 'hormonal', 'endocrine', 'thyroid', 'adrenal', 'testosterone', 'estrogen'],
            'women_health': ['women', 'female', 'pregnancy', 'maternal', 'menopause', 'gynecology'],
            'men_health': ['men', 'male', 'prostate', 'testosterone', 'andrology'],
            'elderly': ['elderly', 'aging', 'senior', 'geriatric', 'age-related'],
            'children': ['children', 'child', 'pediatric', 'infant', 'adolescent', 'teen']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        
        return ','.join(list(set(tags)))  # Remove duplicates

    def save_articles(self, articles: List[Dict]) -> int:
        """Save articles to database and clear cache for immediate frontend updates"""
        saved_count = 0
        
        with sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False) as conn:
            for article in articles:
                try:
                    # Use explicit column names that match the database schema exactly
                    conn.execute("""
                        INSERT OR IGNORE INTO articles 
                        (date, title, authors, summary, url, categories, tags, source, subcategory, url_health)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        article['published_date'],  # Maps to 'date' column
                        article['title'],
                        article.get('author', ''),  # Maps to 'authors' column
                        article['summary'],  # Maps to 'summary' column
                        article['url'],
                        article['category'],  # Maps to 'categories' column
                        article['tags'],
                        article['source'],
                        article.get('subcategory', ''),  # Maps to 'subcategory' column
                        article.get('image_url', '')  # Maps to 'url_health' column for images
                    ))
                    
                    if conn.total_changes > 0:
                        saved_count += 1
                        
                except Exception as e:
                    logger.error(f"Error saving article '{article['title']}': {e}")
            
            conn.commit()
        
    # Cache system removed: always fresh data, no cache invalidation needed
        
        return saved_count

    def run_scraping(self) -> Dict:
        """Run complete scraping process with enhanced sources"""
        logger.info("🚀 Starting Enhanced Master Health Scraper...")
        logger.info(f"📊 Processing {len(self.rss_sources)} RSS sources + Google News + PubMed feeds")
        
        # Initialize database
        self.init_database()
        
        all_articles = []
        
        # Scrape RSS sources (comprehensive list)
        logger.info("📰 Scraping RSS news sources...")
        for source in self.rss_sources:
            articles = self.scrape_rss_source(source)
            all_articles.extend(articles)
            time.sleep(0.5)  # Rate limiting between sources
        
        # Scrape Google News
        logger.info("🔍 Scraping Google News...")
        google_articles = self.scrape_google_news()
        all_articles.extend(google_articles)
        
        # Scrape PubMed research feeds
        logger.info("🧬 Scraping PubMed research feeds...")
        pubmed_articles = self.scrape_pubmed_feeds()
        all_articles.extend(pubmed_articles)
        
        # Save to database
        logger.info("💾 Saving articles to database...")
        saved_count = self.save_articles(all_articles)
        
        result = {
            'total_scraped': len(all_articles),
            'total_saved': saved_count,
            'sources_processed': len(self.rss_sources) + 2,  # +2 for Google News and PubMed
            'rss_sources': len(self.rss_sources),
            'google_news_enabled': FEEDPARSER_AVAILABLE,
            'pubmed_enabled': FEEDPARSER_AVAILABLE,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Enhanced scraping completed: {saved_count}/{len(all_articles)} articles saved")
        return result

def main():
    """Main execution function"""
    scraper = MasterHealthScraper()
    result = scraper.run_scraping()
    
    print("\n" + "="*70)
    print("🏥 ENHANCED MASTER HEALTH SCRAPER - RESULTS")
    print("="*70)
    print(f"📊 Total Articles Scraped: {result['total_scraped']}")
    print(f"💾 Articles Saved to Database: {result['total_saved']}")
    print(f"🌐 Total Sources Processed: {result['sources_processed']}")
    print(f"   └── RSS News Sources: {result['rss_sources']}")
    print(f"   └── Google News: {'✅ Enabled' if result['google_news_enabled'] else '❌ Disabled (Python 3.13)'}")
    print(f"   └── PubMed Research: {'✅ Enabled' if result['pubmed_enabled'] else '❌ Disabled (Python 3.13)'}")
    print(f"⏰ Completed at: {result['timestamp']}")
    print("\n🎯 Enhanced Coverage Areas:")
    print("   • 🧬 Medical & Scientific Research")
    print("   • 🥗 Nutrition & Food Science") 
    print("   • 🌾 Agriculture & Food Policy")
    print("   • 🌫️ Environmental Health & Pollution")
    print("   • 💡 Academic Research (PubMed)")
    print("="*70)
    
    return result

if __name__ == "__main__":
    main()
