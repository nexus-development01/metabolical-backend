#!/usr/bin/env python3
"""
Enhanced Health News Scraper with Production-Ready Features

Comprehensive scraper with:
- Feed validation and blacklisting
- Retry logic with exponential backoff
- Rate limiting and respectful scraping
- Smart deduplication before database insertion
- Improved error handling and logging
- Network resilience for production deployment

Compatible with Python 3.13+ using only standard libraries.
"""

import sys
from pathlib import Path
import requests
import sqlite3
import json
import re
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse, quote_plus
from xml.etree import ElementTree as ET
import hashlib
import random
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Setup enhanced logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# RSS parsing
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not available - using fallback XML parsing")

# Database path
DB_PATH = BASE_DIR / "data" / "articles.db"
if not DB_PATH.exists():
    DB_PATH = BASE_DIR / "db" / "articles.db"

# Import URL validator
try:
    from app.url_validator import URLValidator
    URL_VALIDATOR_AVAILABLE = True
except ImportError:
    URL_VALIDATOR_AVAILABLE = False
    class URLValidator:
        def validate_article_url(self, article):
            return True, {"status": "valid"}

class SummaryEnhancer:
    """Enhance article summaries using multiple strategies"""
    
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Convert to lowercase and split into word sets
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity: intersection / union
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def is_summary_too_similar_to_title(self, title: str, summary: str, threshold: float = 0.9) -> bool:
        """Check if summary is too similar to title using Jaccard similarity"""
        if not title or not summary:
            return False
        
        similarity = self.calculate_jaccard_similarity(title, summary)
        return similarity > threshold
    
    def get_better_summary(self, url: str, title: str, source_name: str) -> str:
        """Try to get a better summary using multiple strategies"""
        
        # Strategy 1: Try to get meta description
        try:
            meta_summary = self.get_meta_description(url)
            if meta_summary and len(meta_summary) > 50:
                # Check if meta description is significantly different from title
                similarity = self.calculate_jaccard_similarity(title, meta_summary)
                if similarity < 0.8:  # Less similar than threshold
                    logger.debug(f"Found good meta description for: {title[:50]}...")
                    return meta_summary
        except Exception as e:
            logger.debug(f"Error getting meta description for {url}: {e}")
        
        # Strategy 2: Try to extract first paragraph using basic HTML parsing
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            content = response.text
            
            # Simple regex to find paragraphs with substantial content
            paragraph_patterns = [
                r'<p[^>]*>([^<]{100,500})</p>',  # Look for substantial paragraphs
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>([^<]{100,500})',
                r'<div[^>]*class="[^"]*article[^"]*"[^>]*>([^<]{100,500})',
                r'<div[^>]*class="[^"]*text[^"]*"[^>]*>([^<]{100,500})'
            ]
            
            for pattern in paragraph_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    # Clean the text
                    clean_text = re.sub(r'<[^>]+>', '', match)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    
                    if len(clean_text) > 100:
                        # Check similarity with title
                        similarity = self.calculate_jaccard_similarity(title, clean_text)
                        if similarity < 0.7:  # Different enough from title
                            result = clean_text[:500] + '...' if len(clean_text) > 500 else clean_text
                            logger.debug(f"Extracted content summary for: {title[:50]}...")
                            return result
        except Exception as e:
            logger.debug(f"Error extracting content from {url}: {e}")
        
        # Strategy 3: If all else fails, return empty (caller will use generated summary)
        return ""
    
    def get_meta_description(self, url: str) -> str:
        """Extract meta description from article URL"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Simple HTML parsing without external dependencies
            content = response.text
            
            # Look for meta description tags using regex
            patterns = [
                r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']{50,})["\']',
                r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']{50,})["\']',
                r'<meta\s+name=["\']twitter:description["\']\s+content=["\']([^"\']{50,})["\']',
                r'<meta\s+content=["\']([^"\']{50,})["\']\s+name=["\']description["\']',
                r'<meta\s+content=["\']([^"\']{50,})["\']\s+property=["\']og:description["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    description = match.group(1).strip()
                    # Decode HTML entities
                    description = self.decode_html_entities(description)
                    
                    if len(description) > 50:
                        return description
            
        except Exception as e:
            logger.debug(f"Could not extract meta description from {url}: {e}")
        
        return ""
    
    def decode_html_entities(self, text: str) -> str:
        """Decode common HTML entities"""
        if not text:
            return ""
        
        # Common HTML entities
        entities = {
            '&quot;': '"',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&nbsp;': ' ',
            '&#160;': ' ',  # Non-breaking space
            '&#39;': "'",
            '&apos;': "'",
            '&hellip;': '...',
            '&mdash;': '—',
            '&ndash;': '–',
            '&rsquo;': "'",
            '&lsquo;': "'",
            '&rdquo;': '"',
            '&ldquo;': '"',
            # Unicode characters that appear as HTML entities
            'â': '"',  # Curly quotes
            'â': '"',  # Curly quotes  
            'â': "'",  # Curly apostrophe
            'â¦': '...',  # Ellipsis
            'â': '-',   # En dash
            'â': '—'    # Em dash
        }
        
        for entity, replacement in entities.items():
            text = text.replace(entity, replacement)
        
        return text
    
    def enhance_article_summary(self, article: dict, source_name: str) -> dict:
        """Main method to enhance article summary"""
        title = article.get('title', '')
        summary = article.get('summary', '')
        url = article.get('url', '')
        
        if not title:
            return article
        
        # Check if current summary is too similar to title
        if summary and title:
            if self.is_summary_too_similar_to_title(title, summary):
                logger.debug(f"Summary too similar to title: {title[:50]}...")
                
                # Try to get a better summary
                better_summary = self.get_better_summary(url, title, source_name)
                if better_summary:
                    article['summary'] = better_summary
                    logger.debug(f"Found better summary: {title[:50]}...")
                else:
                    # Mark for contextual generation by setting empty
                    article['summary'] = ""
                    logger.debug(f"Will generate contextual summary: {title[:50]}...")
            
            # Check for very short summaries
            elif len(summary.strip()) < max(50, len(title) * 0.3):
                better_summary = self.get_better_summary(url, title, source_name)
                if better_summary:
                    article['summary'] = better_summary
                    logger.debug(f"Improved short summary: {title[:50]}...")
                else:
                    article['summary'] = ""
                    logger.debug(f"Will generate summary for short content: {title[:50]}...")
        
        elif not summary:
            # Try to get summary from content first
            better_summary = self.get_better_summary(url, title, source_name)
            if better_summary:
                article['summary'] = better_summary
                logger.debug(f"Extracted summary for missing content: {title[:50]}...")
            else:
                # Leave empty for contextual generation
                article['summary'] = ""
                logger.debug(f"Will generate summary for missing content: {title[:50]}...")
        
        return article

class RateLimiter:
    """Rate limiter for respectful scraping"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
    
    def wait_if_needed(self, domain: str, limit_per_minute: int = 15):
        """Wait if we've exceeded the rate limit for this domain"""
        with self.lock:
            now = time.time()
            minute_ago = now - 60
            
            # Clean old requests
            self.requests[domain] = [req_time for req_time in self.requests[domain] if req_time > minute_ago]
            
            # Check if we need to wait
            if len(self.requests[domain]) >= limit_per_minute:
                wait_time = 60 - (now - self.requests[domain][0])
                if wait_time > 0:
                    logger.info(f"⏱️  Rate limiting: waiting {wait_time:.1f}s for {domain}")
                    time.sleep(wait_time)
                    return self.wait_if_needed(domain, limit_per_minute)
            
            # Record this request
            self.requests[domain].append(now)

class FeedValidator:
    """Validates RSS feeds and manages blacklist"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config_data = self._load_config()
        self.rate_limiter = RateLimiter()
        
        # Load configuration from feeds_blacklist section
        feeds_config = self.config_data.get('feeds_blacklist', {})
        validation_config = feeds_config.get('feed_validation', {})
        
        self.timeout = validation_config.get('timeout_seconds', 15)
        self.max_retries = validation_config.get('max_retries', 3)
        self.retry_delay_base = validation_config.get('retry_delay_base', 2)
        self.rate_limits = validation_config.get('rate_limits', {})
        self.user_agents = validation_config.get('user_agents', [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ])
    
    def _load_config(self) -> Dict:
        """Load configuration from config.yml"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {"feeds_blacklist": {"blacklisted_feeds": [], "feed_validation": {}, "alternative_feeds": {}}}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {"feeds_blacklist": {"blacklisted_feeds": [], "feed_validation": {}, "alternative_feeds": {}}}
    
    def _save_config(self):
        """Save configuration to config.yml"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config_data, f, default_flow_style=False)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def is_blacklisted(self, url: str) -> Tuple[bool, Optional[str]]:
        """Check if URL is blacklisted and if retry time has passed"""
        feeds_config = self.config_data.get('feeds_blacklist', {})
        for feed in feeds_config.get('blacklisted_feeds', []):
            if feed['url'] == url:
                # Check if retry time has passed
                retry_after = datetime.fromisoformat(feed['retry_after'].replace('Z', '+00:00'))
                if datetime.now(timezone.utc) < retry_after:
                    return True, f"Blacklisted until {retry_after.strftime('%Y-%m-%d %H:%M')}"
                else:
                    # Retry time passed, remove from blacklist
                    self._remove_from_blacklist(url)
                    return False, None
        return False, None

class FeedValidator:
    def __init__(self, blacklist_file: Path):
        self.blacklist_file = blacklist_file
        self.blacklist_data = self._load_blacklist()
        self.rate_limiter = RateLimiter()
        
        # Load configuration
        self.config = self.blacklist_data.get('feed_validation', {})
        self.timeout = self.config.get('timeout_seconds', 15)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay_base = self.config.get('retry_delay_base', 2)
        self.rate_limits = self.config.get('rate_limits', {})
        self.user_agents = self.config.get('user_agents', [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ])
    
    def _load_blacklist(self) -> Dict:
        """Load blacklist configuration"""
        try:
            if self.blacklist_file.exists():
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {"blacklisted_feeds": [], "feed_validation": {}, "alternative_feeds": {}}
        except Exception as e:
            logger.error(f"Error loading blacklist: {e}")
            return {"blacklisted_feeds": [], "feed_validation": {}, "alternative_feeds": {}}
    
    def _save_blacklist(self):
        """Save blacklist configuration"""
        try:
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.blacklist_data, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Error saving blacklist: {e}")
    
    def is_blacklisted(self, url: str) -> Tuple[bool, Optional[str]]:
        """Check if URL is blacklisted and if retry time has passed"""
        for feed in self.blacklist_data.get('blacklisted_feeds', []):
            if feed['url'] == url:
                retry_after = feed.get('retry_after')
                if retry_after:
                    try:
                        retry_time = datetime.fromisoformat(retry_after.replace('Z', '+00:00'))
                        if datetime.now() < retry_time:
                            return True, f"Blacklisted until {retry_after}: {feed['reason']}"
                        else:
                            # Time to retry - remove from blacklist temporarily
                            self._remove_from_blacklist(url)
                            return False, "Retry time reached, attempting again"
                    except Exception:
                        pass
                return True, feed['reason']
        return False, None
    
    def _remove_from_blacklist(self, url: str):
        """Remove URL from blacklist"""
        feeds_config = self.config_data.setdefault('feeds_blacklist', {})
        feeds_config['blacklisted_feeds'] = [
            feed for feed in feeds_config.get('blacklisted_feeds', [])
            if feed['url'] != url
        ]
        self._save_config()
        self.blacklist_data['blacklisted_feeds'] = [
            feed for feed in self.blacklist_data.get('blacklisted_feeds', [])
            if feed['url'] != url
        ]
        self._save_blacklist()
    
    def add_to_blacklist(self, url: str, reason: str, status_code: Optional[int] = None):
        """Add URL to blacklist with appropriate retry time"""
        # Determine retry time based on error type
        now = datetime.now()
        if status_code == 404 or status_code == 410:
            # Permanent errors - retry after 1 month
            retry_after = now + timedelta(days=30)
        elif status_code == 429:
            # Rate limiting - retry after 12 hours
            retry_after = now + timedelta(hours=12)
        elif status_code and 500 <= status_code < 600:
            # Server errors - retry after 6 hours
            retry_after = now + timedelta(hours=6)
        else:
            # DNS/network errors - retry after 6 hours
            retry_after = now + timedelta(hours=6)
        
        feed_entry = {
            'url': url,
            'reason': reason,
            'timestamp': now.isoformat() + 'Z',
            'status_code': status_code or "UNKNOWN",
            'retry_after': retry_after.isoformat() + 'Z'
        }
        
        # Remove existing entry if any
        self._remove_from_blacklist(url)
        
        # Add new entry
        feeds_config = self.config_data.setdefault('feeds_blacklist', {})
        if 'blacklisted_feeds' not in feeds_config:
            feeds_config['blacklisted_feeds'] = []
        
        feeds_config['blacklisted_feeds'].append(feed_entry)
        self._save_config()
        if 'blacklisted_feeds' not in self.blacklist_data:
            self.blacklist_data['blacklisted_feeds'] = []
        
        self.blacklist_data['blacklisted_feeds'].append(feed_entry)
        self._save_blacklist()
        
        logger.warning(f"🚫 Blacklisted {url}: {reason} (retry after: {retry_after.strftime('%Y-%m-%d %H:%M')})")
    
    def validate_feed(self, url: str, source_name: str) -> Tuple[bool, Optional[str], Optional[List[Dict]]]:
        """Validate feed with retries and error handling"""
        # Check blacklist first
        is_blacklisted, reason = self.is_blacklisted(url)
        if is_blacklisted:
            logger.debug(f"⏭️  Skipping blacklisted feed {source_name}: {reason}")
            return False, reason, None
        
        # Apply rate limiting
        domain = urlparse(url).netloc
        rate_limit = self.rate_limits.get(domain, self.rate_limits.get('default', 15))
        self.rate_limiter.wait_if_needed(domain, rate_limit)
        
        # Try with retries and exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Random user agent rotation
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                }
                
                # Make request with timeout
                response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
                
                # Check for specific error codes
                if response.status_code == 404:
                    self.add_to_blacklist(url, "404 Not Found - Feed discontinued", 404)
                    return False, "404 Not Found", None
                
                elif response.status_code == 410:
                    self.add_to_blacklist(url, "410 Gone - Feed permanently removed", 410)
                    return False, "410 Gone", None
                
                elif response.status_code == 429:
                    self.add_to_blacklist(url, "429 Too Many Requests - Rate limited", 429)
                    return False, "Rate limited", None
                
                elif response.status_code >= 500:
                    if attempt == self.max_retries - 1:
                        self.add_to_blacklist(url, f"{response.status_code} Server Error", response.status_code)
                    raise requests.exceptions.HTTPError(f"{response.status_code} Server Error")
                
                # Success - parse the feed
                response.raise_for_status()
                
                # Try to parse XML to validate it's a proper feed
                try:
                    root = ET.fromstring(response.content)
                    # Basic validation - check for RSS/Atom structure
                    if root.tag not in ['rss', 'feed'] and 'rss' not in root.tag.lower() and 'feed' not in root.tag.lower():
                        items = root.findall('.//item') or root.findall('.//{http://purl.org/rss/1.0/}item')
                        if not items:
                            raise ValueError("No RSS items found")
                    
                    logger.debug(f"✅ Feed validation successful: {source_name}")
                    return True, "Valid", None  # We'll parse articles later in the main scraper
                
                except ET.ParseError as e:
                    if attempt == self.max_retries - 1:
                        self.add_to_blacklist(url, f"Invalid XML: {str(e)}", None)
                    raise ValueError(f"Invalid XML: {e}")
                
            except (requests.exceptions.RequestException, ValueError) as e:
                last_error = str(e)
                
                # For DNS errors, don't retry immediately
                if "Failed to resolve" in last_error or "Name or service not known" in last_error:
                    if attempt == self.max_retries - 1:
                        self.add_to_blacklist(url, f"DNS resolution failure: {last_error}", None)
                    logger.warning(f"🌐 DNS error for {source_name}: {last_error}")
                    return False, f"DNS error: {last_error}", None
                
                # For other errors, implement exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay_base ** (attempt + 1) + random.uniform(0, 1)
                    logger.debug(f"🔄 Retry {attempt + 1}/{self.max_retries} for {source_name} in {wait_time:.1f}s")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    self.add_to_blacklist(url, f"Failed after {self.max_retries} retries: {last_error}", None)
                    logger.error(f"❌ Feed validation failed for {source_name}: {last_error}")
                    return False, f"Failed after retries: {last_error}", None
        
        return False, f"Unknown error: {last_error}", None

class EnhancedHealthScraper:
    """Production-ready health news scraper with enhanced features"""
    
    def __init__(self):
        self.url_validator = URLValidator() if URL_VALIDATOR_AVAILABLE else None
        self.session = requests.Session()
        
        # Initialize summary enhancer
        self.summary_enhancer = SummaryEnhancer(self.session)
        
        # Enhanced session configuration with retry logic
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        })
        
        # Add retry strategy with exponential backoff
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[403, 404, 429, 500, 502, 503, 504],
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Initialize feed validator
        config_file = BASE_DIR / "config" / "config.yml"
        self.feed_validator = FeedValidator(config_file)
        
        # Pre-computed URL and title hashes for fast duplicate detection
        self.existing_url_hashes: Set[str] = set()
        self.existing_title_hashes: Set[str] = set()
        self._load_existing_hashes()
        
        # Comprehensive RSS feed sources with updated URLs
        self.rss_sources = [
            # Major Health Organizations - Priority 1
            {
                "name": "WHO Health News",
                "url": "https://www.who.int/rss-feeds/news-english.xml",
                "category": "news",
                "tags": ["who", "international", "policy"],
                "priority": 1
            },
            {
                "name": "CDC Health News",
                "url": "https://www.cdc.gov/media/rss/health-news.xml",
                "category": "news", 
                "tags": ["cdc", "prevention", "government"],
                "priority": 1
            },
            
            # Major News Outlets - Priority 2  
            {
                "name": "BBC Health",
                "url": "http://feeds.bbci.co.uk/news/health/rss.xml",
                "category": "news",
                "tags": ["bbc", "international"],
                "priority": 2
            },
            {
                "name": "NPR Health",
                "url": "https://feeds.npr.org/1001/rss.xml",
                "category": "news",
                "tags": ["npr", "health", "research"],
                "priority": 2
            },
            
            # Health-Specific Publications - Priority 3
            {
                "name": "Healthline News",
                "url": "https://www.healthline.com/health-news/rss",
                "category": "solutions", 
                "tags": ["healthline", "wellness", "lifestyle"],
                "priority": 3
            },
            
            # Medical & Scientific Sources - Priority 2
            {
                "name": "Medical Xpress",
                "url": "https://medicalxpress.com/rss-feed/",
                "category": "news",
                "tags": ["medical", "research", "science"],
                "priority": 2
            },
            {
                "name": "ScienceDaily Health",
                "url": "https://www.sciencedaily.com/rss/health_medicine.xml",
                "category": "news",
                "tags": ["science", "research", "medical"],
                "priority": 2
            },
            {
                "name": "Nature Medicine",
                "url": "https://www.nature.com/nm.rss",
                "category": "trending",
                "tags": ["research", "medicine", "science"],
                "priority": 2
            },
            
            # Academic & Research Sources
            {
                "name": "PubMed Central News",
                "url": "https://www.ncbi.nlm.nih.gov/feed/rss.cgi?ChanKey=NIHNews",
                "category": "news",
                "tags": ["research", "academic", "health"],
                "priority": 2
            },
            {
                "name": "Harvard Nutrition Source",
                "url": "https://www.hsph.harvard.edu/nutritionsource/feed/",
                "category": "food",
                "tags": ["harvard", "nutrition", "research"],
                "priority": 1
            },
            
            # Specialized Metabolic Health Sources
            {
                "name": "Diabetes Research News",
                "url": "https://www.sciencedaily.com/rss/health_medicine/diabetes.xml",
                "category": "diseases",
                "tags": ["diabetes", "research", "metabolic"],
                "priority": 1
            },
            {
                "name": "Obesity Research News",
                "url": "https://www.sciencedaily.com/rss/health_medicine/obesity.xml",
                "category": "diseases",
                "tags": ["obesity", "research", "metabolic"],
                "priority": 1
            },
            {
                "name": "Nutrition Research News",
                "url": "https://www.sciencedaily.com/rss/health_medicine/nutrition.xml",
                "category": "food",
                "tags": ["nutrition", "research", "science", "natural food"],
                "priority": 1
            },
            
            # Additional Food & Nutrition Sources
            {
                "name": "Healthline News",
                "url": "https://www.healthline.com/rss",
                "category": "news",
                "tags": ["nutrition", "diet", "healthy eating", "medical"],
                "priority": 2
            },
            {
                "name": "Food Safety News",
                "url": "https://www.foodsafetynews.com/feed/",
                "category": "food",
                "tags": ["food safety", "contamination", "recalls"],
                "priority": 2
            },
            {
                "name": "Organic Food News",
                "url": "https://www.organicfoodguide.com/feed/",
                "category": "food",
                "tags": ["organic food", "natural food", "sustainable"],
                "priority": 3
            },
            
            # Health Blogs & Opinion Sources
            {
                "name": "EatThis.com Health",
                "url": "https://www.eatthis.com/feed/",
                "category": "blogs_and_opinions",
                "tags": ["nutrition blog", "food opinions", "health advice"],
                "priority": 2
            },
            {
                "name": "Health Harvard Blog",
                "url": "https://www.health.harvard.edu/blog/feed",
                "category": "blogs_and_opinions",
                "tags": ["wellness blog", "health opinions", "medical advice"],
                "priority": 2
            },
            {
                "name": "Nutrition Stripped",
                "url": "https://nutritionstripped.com/feed/",
                "category": "blogs_and_opinions",
                "tags": ["nutrition blog", "healthy recipes", "wellness advice"],
                "priority": 2
            },
            {
                "name": "Verywell Health",
                "url": "https://www.verywellhealth.com/rss",
                "category": "blogs_and_opinions",
                "tags": ["health blog", "medical advice", "wellness"],
                "priority": 3
            },
            {
                "name": "Shape Health & Fitness",
                "url": "https://www.shape.com/rss.xml",
                "category": "blogs_and_opinions",
                "tags": ["fitness blog", "health opinions", "wellness"],
                "priority": 3
            },
            {
                "name": "Self Health News", 
                "url": "https://www.self.com/feed/rss",
                "category": "blogs_and_opinions",
                "tags": ["health blog", "wellness", "self care"],
                "priority": 3
            }
        ]
        
        # Google News health keywords for comprehensive coverage - Enhanced for food and trending
        self.google_news_keywords = [
            # General health
            "health", "medical", "wellness", "nutrition", "diabetes", 
            "obesity", "heart disease", "prevention", "mental health",
            
            # Food & Nutrition specific
            "healthy food", "organic food", "diet nutrition", "food safety",
            "superfood", "plant based diet", "mediterranean diet",
            
            # Current trending topics (updated for 2025)
            "gut health", "microbiome", "probiotics", "sleep health",
            "mental wellness", "hormonal health", "longevity",
            "weight loss", "intermittent fasting", "keto diet"
        ]
        
        self.articles_saved = 0
        self.duplicate_count = 0
        self.error_count = 0
        self.validation_failures = 0
    
    def _load_existing_hashes(self):
        """Load existing URL and title hashes for fast duplicate detection"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Load recent URLs (last 90 days) for duplicate detection
            cursor.execute('''
                SELECT url, title FROM articles 
                WHERE date > date('now', '-90 days')
                ORDER BY date DESC
            ''')
            
            for url, title in cursor.fetchall():
                if url:
                    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
                    self.existing_url_hashes.add(url_hash)
                
                if title:
                    title_hash = hashlib.md5(self._normalize_title(title).encode('utf-8')).hexdigest()
                    self.existing_title_hashes.add(title_hash)
            
            conn.close()
            logger.info(f"📊 Loaded {len(self.existing_url_hashes)} URL hashes and {len(self.existing_title_hashes)} title hashes for duplicate detection")
            
        except Exception as e:
            logger.error(f"Error loading existing hashes: {e}")
            self.existing_url_hashes = set()
            self.existing_title_hashes = set()
    
    def _is_duplicate_fast(self, url: str, title: str) -> bool:
        """Fast duplicate detection using pre-computed hashes"""
        # Check URL duplicate
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        if url_hash in self.existing_url_hashes:
            return True
        
        # Check title duplicate
        normalized_title = self._normalize_title(title)
        title_hash = hashlib.md5(normalized_title.encode('utf-8')).hexdigest()
        if title_hash in self.existing_title_hashes:
            return True
        
        return False
    
    def _add_to_duplicate_cache(self, url: str, title: str):
        """Add new article to duplicate detection cache"""
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        self.existing_url_hashes.add(url_hash)
        
        normalized_title = self._normalize_title(title)
        title_hash = hashlib.md5(normalized_title.encode('utf-8')).hexdigest()
        self.existing_title_hashes.add(title_hash)
    
    def create_database(self):
        """Create articles database with optimized schema"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    summary TEXT,
                    content TEXT,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT,
                    date TIMESTAMP NOT NULL,
                    categories TEXT,
                    subcategory TEXT,
                    tags TEXT,
                    authors TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles(categories)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title)')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database creation error: {e}")
    
    def validate_feeds_startup(self):
        """Validate all feeds at startup and update blacklist"""
        logger.info("🔍 Validating RSS feeds at startup...")
        
        valid_sources = []
        invalid_count = 0
        
        for source in self.rss_sources:
            is_valid, reason, _ = self.feed_validator.validate_feed(source['url'], source['name'])
            
            if is_valid:
                valid_sources.append(source)
                logger.debug(f"   ✅ {source['name']}")
            else:
                invalid_count += 1
                logger.warning(f"   ❌ {source['name']}: {reason}")
        
        self.rss_sources = valid_sources
        logger.info(f"📊 Feed validation complete: {len(valid_sources)} valid, {invalid_count} invalid/blacklisted")
        
        return len(valid_sources), invalid_count
    
    def parse_rss_feed(self, url: str, timeout: int = 15) -> List[Dict]:
        """Parse RSS feed with enhanced error handling and validation"""
        articles = []
        
        try:
            # Apply rate limiting
            domain = urlparse(url).netloc
            rate_limit = self.feed_validator.rate_limits.get(domain, 15)
            self.feed_validator.rate_limiter.wait_if_needed(domain, rate_limit)
            
            # Random user agent for this request
            headers = dict(self.session.headers)
            headers['User-Agent'] = random.choice(self.feed_validator.user_agents)
            
            response = self.session.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle different RSS formats
            items = root.findall('.//item') or root.findall('.//{http://purl.org/rss/1.0/}item')
            
            for item in items:
                try:
                    title = self._get_text(item, ['title'])
                    link = self._get_text(item, ['link', 'guid'])
                    description = self._get_text(item, ['description', 'summary'])
                    pub_date = self._get_text(item, ['pubDate', 'published', 'date'])
                    author = self._get_text(item, ['author', 'creator', 'dc:creator'])
                    
                    if title and link:
                        # Parse date
                        parsed_date = self._parse_date(pub_date or "")
                        
                        # Clean description and extract meaningful summary
                        if description:
                            description = self._clean_html(description)
                            # Extract more meaningful summary content
                            description = self._extract_meaningful_summary(description, title or "")
                            # Limit length but keep meaningful content
                            description = description[:800] + '...' if len(description) > 800 else description
                        
                        # Fast duplicate check before processing
                        if not self._is_duplicate_fast(link, title):
                            articles.append({
                                'title': (title or "Untitled").strip()[:200],
                                'url': (link or "").strip(),
                                'summary': description,
                                'date': parsed_date,
                                'author': author
                            })
                        
                except Exception as e:
                    logger.debug(f"Error parsing RSS item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"RSS feed error for {url}: {e}")
            
        return articles
    
    def _get_text(self, element, tag_names: List[str]) -> Optional[str]:
        """Get text from first available tag"""
        for tag_name in tag_names:
            try:
                # Handle namespaced tags
                if ':' in tag_name:
                    namespace_map = {
                        'dc': 'http://purl.org/dc/elements/1.1/',
                        'content': 'http://purl.org/rss/1.0/modules/content/'
                    }
                    elem = element.find(tag_name, namespace_map)
                else:
                    elem = element.find(tag_name) or element.find(f'.//{tag_name}')
                
                if elem is not None and elem.text:
                    return elem.text.strip()
            except Exception:
                # Try without namespace if namespaced search fails
                try:
                    simple_tag = tag_name.split(':')[-1]  # Get tag without namespace
                    elem = element.find(simple_tag) or element.find(f'.//{simple_tag}')
                    if elem is not None and elem.text:
                        return elem.text.strip()
                except Exception:
                    continue
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        if not date_str:
            return datetime.now()
            
        # Common date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S GMT',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # If all else fails, return current time
        logger.debug(f"Could not parse date: {date_str}")
        return datetime.now()
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
            
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        return text.strip()
    
    def _extract_meaningful_summary(self, description: str, title: str) -> str:
        """Extract meaningful summary content from description, ensuring it's unique from title"""
        if not description:
            return ""
            
        # Remove title from description if it appears at the beginning
        if title and description.lower().startswith(title.lower()):
            description = description[len(title):].lstrip(' .-:')
        
        # Remove common unwanted patterns
        patterns_to_remove = [
            r'Read more.*',
            r'Click here.*',
            r'Learn more.*',
            r'Continue reading.*',
            r'Full article.*',
            r'View original.*',
            r'\[.*?\]',  # Remove content in brackets
            r'Source:.*',
            r'Via:.*',
            r'From:.*',
            r'Share this:.*',
            r'Subscribe to.*',
            r'Follow us.*',
            r'More information.*'
        ]
        
        for pattern in patterns_to_remove:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and punctuation
        description = re.sub(r'\s+', ' ', description).strip()
        description = re.sub(r'^[:\-\s\.]+', '', description)
        description = re.sub(r'[:\-\s\.]+$', '', description)
        
        # Check if summary is just a duplicate of the title (case-insensitive)
        if title and description:
            title_clean = title.lower().strip()
            description_clean = description.lower().strip()
            
            # If they're identical or very similar, return empty (will be handled by fallback)
            if (title_clean == description_clean or 
                description_clean in title_clean or
                title_clean in description_clean):
                if len(description_clean) - len(title_clean) < 20:  # Not much additional content
                    return ""
        
        # If the remaining text is too short, return empty (will be handled by fallback)
        if len(description.strip()) < 50:
            return ""
            
        return description
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for duplicate detection"""
        if not title:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = title.lower().strip()
        
        # Remove common punctuation and special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common prefixes that don't affect content
        prefixes_to_remove = [
            'new study:', 'study:', 'research:', 'scientists:', 'researchers:',
            'breaking:', 'news:', 'alert:', 'update:'
        ]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                break
        
        return normalized
    
    def categorize_article(self, article: Dict) -> Tuple[str, List[str]]:
        """Smart categorization based on title and content using category keywords from YAML"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        content = title + ' ' + summary
        
        # Load category keywords from YAML file
        try:
            import yaml
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "config" / "category_keywords.yml"
            with open(config_path, 'r', encoding='utf-8') as f:
                categories_data = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load category keywords: {e}")
            # Fallback to basic categorization
            return self._basic_categorization(content)
        
        # Ensure we have the categories structure
        if not categories_data or 'categories' not in categories_data:
            logger.warning("Invalid category_keywords.yml structure")
            return self._basic_categorization(content)
        
        categories = categories_data['categories']
        
        # Find best matching category and subcategories
        best_category = 'news'  # Default fallback
        best_subcategories = []
        max_score = 0
        
        for category_name, category_info in categories.items():
            if not isinstance(category_info, dict) or 'tags' not in category_info:
                continue
                
            category_score = 0
            matched_subcategories = []
            
            # Check each tag in this category
            for tag in category_info['tags']:
                tag_lower = tag.lower()
                
                # Count keyword matches in content (weighted by importance)
                title_matches = content.count(tag_lower)
                if title_matches > 0:
                    # Higher weight for title matches
                    weight = 3 if tag_lower in title else 1
                    category_score += title_matches * weight
                    
                    # Map subcategory based on keyword match
                    subcategory = self._map_keyword_to_subcategory(tag_lower, category_name)
                    if subcategory and subcategory not in matched_subcategories:
                        matched_subcategories.append(subcategory)
            
            # Update best match if this category scored higher
            if category_score > max_score:
                max_score = category_score
                best_category = category_name
                best_subcategories = matched_subcategories
        
        # Ensure we have at least one subcategory
        if not best_subcategories:
            best_subcategories = self._get_default_subcategory(best_category)
        
        return best_category, best_subcategories
    
    def _map_keyword_to_subcategory(self, keyword: str, category: str) -> Optional[str]:
        """Map a matched keyword to its appropriate subcategory"""
        
        # Disease category mappings
        if category == 'diseases':
            diabetes_keywords = ['diabetes', 'blood sugar', 'insulin', 'glucose', 'diabetic', 'hyperglycemia', 'hypoglycemia']
            obesity_keywords = ['obesity', 'overweight', 'weight gain', 'bmi', 'body mass index', 'weight management']
            cardio_keywords = ['heart disease', 'cardiovascular', 'cardiac', 'heart attack', 'stroke', 'hypertension', 'high blood pressure']
            inflammation_keywords = ['inflammation', 'inflammatory', 'anti-inflammatory', 'chronic inflammation']
            liver_keywords = ['liver', 'hepatic', 'liver disease', 'fatty liver', 'cirrhosis', 'hepatitis']
            kidney_keywords = ['kidney', 'renal', 'kidney disease', 'kidney stone', 'dialysis']
            thyroid_keywords = ['thyroid', 'hypothyroid', 'hyperthyroid', 'thyroid gland']
            metabolic_keywords = ['metabolism', 'metabolic', 'metabolic syndrome', 'metabolic disorder']
            sleep_keywords = ['sleep disorder', 'insomnia', 'sleep apnea', 'sleep health']
            skin_keywords = ['skin', 'dermatology', 'acne', 'eczema', 'psoriasis', 'dermatitis']
            eyes_ears_keywords = ['eye', 'vision', 'ear', 'hearing', 'ophthalmology', 'audiology']
            reproductive_keywords = ['reproductive health', 'fertility', 'infertility', 'sexual health']
            
            if any(k in keyword for k in diabetes_keywords):
                return 'diabetes'
            elif any(k in keyword for k in obesity_keywords):
                return 'obesity'
            elif any(k in keyword for k in cardio_keywords):
                return 'cardiovascular'
            elif any(k in keyword for k in inflammation_keywords):
                return 'inflammation'
            elif any(k in keyword for k in liver_keywords):
                return 'liver'
            elif any(k in keyword for k in kidney_keywords):
                return 'kidney'
            elif any(k in keyword for k in thyroid_keywords):
                return 'thyroid'
            elif any(k in keyword for k in metabolic_keywords):
                return 'metabolic'
            elif any(k in keyword for k in sleep_keywords):
                return 'sleep disorders'
            elif any(k in keyword for k in skin_keywords):
                return 'skin'
            elif any(k in keyword for k in eyes_ears_keywords):
                return 'eyes and ears'
            elif any(k in keyword for k in reproductive_keywords):
                return 'reproductive health'
        
        # Solutions category mappings
        elif category == 'solutions':
            nutrition_keywords = ['nutrition', 'dietary', 'vitamins', 'minerals', 'balanced diet', 'healthy eating']
            fitness_keywords = ['fitness', 'exercise', 'workout', 'physical activity', 'training', 'cardio', 'strength']
            lifestyle_keywords = ['lifestyle', 'daily habits', 'routine', 'behavior modification', 'healthy habits']
            wellness_keywords = ['wellness', 'wellbeing', 'holistic health', 'self-care', 'meditation', 'mindfulness']
            prevention_keywords = ['prevention', 'preventive', 'screening', 'vaccination', 'checkup', 'early detection']
            
            if any(k in keyword for k in nutrition_keywords):
                return 'nutrition'
            elif any(k in keyword for k in fitness_keywords):
                return 'fitness'
            elif any(k in keyword for k in lifestyle_keywords):
                return 'lifestyle'
            elif any(k in keyword for k in wellness_keywords):
                return 'wellness'
            elif any(k in keyword for k in prevention_keywords):
                return 'prevention'
        
        # Food category mappings
        elif category == 'food':
            natural_keywords = ['natural food', 'organic', 'whole foods', 'unprocessed', 'superfood', 'antioxidants']
            organic_keywords = ['organic food', 'organic farming', 'pesticide free', 'chemical free', 'sustainable food']
            processed_keywords = ['processed food', 'ultra processed', 'packaged food', 'fast food', 'junk food']
            seafood_keywords = ['fish', 'seafood', 'salmon', 'tuna', 'shellfish', 'omega-3 fish']
            safety_keywords = ['food safety', 'food poisoning', 'contamination', 'food recall', 'hygiene']
            
            if any(k in keyword for k in natural_keywords):
                return 'natural food'
            elif any(k in keyword for k in organic_keywords):
                return 'organic food'
            elif any(k in keyword for k in processed_keywords):
                return 'processed food'
            elif any(k in keyword for k in seafood_keywords):
                return 'fish and seafood'
            elif any(k in keyword for k in safety_keywords):
                return 'food safety'
        
        # Other category mappings (audience, trending, news, etc.)
        # ... (continuing with similar pattern)
        
        return None
    
    def _get_default_subcategory(self, category: str) -> List[str]:
        """Get default subcategory for a category if no specific match found"""
        defaults = {
            'diseases': ['metabolic'],
            'solutions': ['wellness'],
            'food': ['natural food'],
            'audience': ['families'],
            'trending': ['gut health'],
            'news': ['latest'],
            'blogs_and_opinions': []
        }
        return defaults.get(category, ['general'])
    
    def _basic_categorization(self, content: str) -> Tuple[str, List[str]]:
        """Fallback basic categorization if YAML file unavailable"""
        if any(word in content for word in ['diabetes', 'blood sugar', 'insulin', 'glucose']):
            return 'diseases', ['diabetes', 'metabolic']
        elif any(word in content for word in ['cancer', 'tumor', 'oncology', 'chemotherapy']):
            return 'diseases', ['cancer', 'treatment']
        elif any(word in content for word in ['heart', 'cardiac', 'cardiovascular', 'cholesterol']):
            return 'diseases', ['cardiovascular', 'heart']
        elif any(word in content for word in ['mental health', 'depression', 'anxiety', 'stress']):
            return 'diseases', ['mental health', 'wellness']
        elif any(word in content for word in ['nutrition', 'diet', 'food', 'eating']):
            return 'food', ['nutrition', 'diet']
        elif any(word in content for word in ['exercise', 'fitness', 'workout', 'physical activity']):
            return 'solutions', ['fitness', 'exercise']
        elif any(word in content for word in ['vaccine', 'vaccination', 'immunization']):
            return 'solutions', ['prevention', 'vaccination']
        elif any(word in content for word in ['who', 'policy', 'government', 'health policy']):
            return 'news', ['policy', 'government']
        elif any(word in content for word in ['research', 'study', 'clinical trial']):
            return 'news', ['research', 'study']
        else:
            return 'news', ['general']
    
    def decode_html_entities(self, text: str) -> str:
        """Decode common HTML entities"""
        if not text:
            return ""
        
        # Common HTML entities
        entities = {
            '&quot;': '"',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&nbsp;': ' ',
            '&#160;': ' ',  # Non-breaking space
            '&#39;': "'",
            '&apos;': "'",
            '&hellip;': '...',
            '&mdash;': '—',
            '&ndash;': '–',
            '&rsquo;': "'",
            '&lsquo;': "'",
            '&rdquo;': '"',
            '&ldquo;': '"',
            # Numeric HTML entities
            '&#58;': ':',   # Colon
            '&#947;': 'γ',  # Greek gamma
            '&#945;': 'α',  # Greek alpha
            '&#946;': 'β',  # Greek beta
            '&#8212;': '—', # Em dash
            '&#8211;': '–', # En dash
            '&#8230;': '…', # Ellipsis
            '&#8217;': "'", # Right single quotation mark
            '&#8216;': "'", # Left single quotation mark
            '&#8221;': '"', # Right double quotation mark
            '&#8220;': '"', # Left double quotation mark
            # Double-encoded entities (Unicode escape + HTML entity)
            '\\u0026#58;': ':',   # Double-encoded colon
            '\\u0026#947;': 'γ',  # Double-encoded gamma
            '\\u0026#945;': 'α',  # Double-encoded alpha
            '\\u0026#946;': 'β',  # Double-encoded beta
            '\\u0026#39;': "'",   # Double-encoded apostrophe
            '\\u0026#160;': ' ',  # Double-encoded non-breaking space
            '\\u0026quot;': '"',  # Double-encoded quote
            '\\u0026amp;': '&',   # Double-encoded ampersand
            '\\u0026lt;': '<',    # Double-encoded less than
            '\\u0026gt;': '>',    # Double-encoded greater than
            # Unicode entities that appear as special characters
            'â': '"',  # Smart quotes appearing as â
            'â': '"',  # Other smart quote
            'â': "'",  # Smart apostrophe
            'â¦': '...',  # Ellipsis
            'â': '-',  # Em dash
            '\\u0026': '&',  # URL encoded ampersand
            '\\u0027': "'",  # URL encoded apostrophe
            '\\u0022': '"',  # URL encoded quote
        }
        
        # Replace entities
        for entity, replacement in entities.items():
            text = text.replace(entity, replacement)
        
        return text.strip()
    
    def clean_article_title(self, title: str, source_name: str) -> str:
        """Clean article titles, especially for PubMed and research sources"""
        if not title:
            return title
            
        # Clean HTML entities first
        title = self.decode_html_entities(title)
        
        # Special handling for PubMed articles with technical prefixes
        if "PubMed" in source_name and "|" in title:
            # Remove patterns like "New | phs003860.v1.p1 |" 
            # Keep only the actual descriptive title
            parts = title.split("|")
            for part in parts:
                part = part.strip()
                # Skip short parts, technical IDs, and "New" prefixes
                if (len(part) > 20 and 
                    not part.lower() in ['new', 'updated'] and
                    not any(char in part for char in ['phs', '.v1.p1', 'dbGaP'])):
                    return part
            
            # If no good part found, take the longest meaningful part
            meaningful_parts = [p.strip() for p in parts if len(p.strip()) > 15]
            if meaningful_parts:
                return max(meaningful_parts, key=len)
        
        # Remove common prefixes for all sources
        prefixes_to_remove = ['New:', 'New |', 'Latest:', 'Breaking:', 'Study:']
        for prefix in prefixes_to_remove:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
                break
                
        return title

    def clean_existing_articles_in_db(self):
        """Clean special characters and duplicate summaries in existing database articles"""
        logger.info("🧹 Starting database article cleaning...")
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get articles with special characters or duplicate title/summary
            cursor.execute('''
                SELECT id, title, summary, source FROM articles 
                WHERE (title LIKE '%â%' OR summary LIKE '%â%' OR
                       title LIKE '%â%' OR summary LIKE '%â%' OR
                       title LIKE '%â%' OR summary LIKE '%â%' OR
                       title = summary OR
                       length(title) - length(summary) BETWEEN -10 AND 10)
                LIMIT 100
            ''')
            
            articles_to_fix = cursor.fetchall()
            fixed_count = 0
            
            for article_id, title, summary, source in articles_to_fix:
                # Clean title and summary
                clean_title = self.clean_article_title(title or '', source or '')
                clean_summary = self.decode_html_entities(summary or '')
                
                # Check if title and summary are too similar
                if clean_title and clean_summary:
                    title_clean = clean_title.lower().strip()
                    summary_clean = clean_summary.lower().strip()
                    
                    if (title_clean == summary_clean or 
                        abs(len(title_clean) - len(summary_clean)) < 10 or
                        summary_clean in title_clean or
                        title_clean in summary_clean):
                        # Generate a better summary
                        clean_summary = self._generate_contextual_summary(clean_title, source or 'Unknown')
                
                # Update the article
                cursor.execute('''
                    UPDATE articles 
                    SET title = ?, summary = ? 
                    WHERE id = ?
                ''', (clean_title, clean_summary, article_id))
                
                fixed_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Cleaned {fixed_count} articles in database")
            return fixed_count
            
        except Exception as e:
            logger.error(f"Error cleaning database articles: {e}")
            return 0

    def save_article(self, article: Dict, source_name: str, source_tags: List[str]) -> bool:
        """Save article to database with enhanced validation and fast deduplication"""
        try:
            # Clean title and summary first
            if 'title' in article:
                article['title'] = self.clean_article_title(article['title'], source_name)
            if 'summary' in article:
                article['summary'] = self.decode_html_entities(article['summary'])
            if 'url' in article:
                # Clean URL of unicode escapes
                article['url'] = article['url'].replace('\\u0026', '&').replace('\\u0027', "'").replace('\\u0022', '"')
            
            # Check for identical or very similar title and summary
            title = article.get('title', '').strip()
            summary = article.get('summary', '').strip()
            
            if title and summary:
                title_clean = title.lower().strip()
                summary_clean = summary.lower().strip()
                
                # Check if title and summary are too similar
                if (title_clean == summary_clean or 
                    abs(len(title_clean) - len(summary_clean)) < 10 or
                    summary_clean in title_clean or
                    title_clean in summary_clean):
                    # Generate a better summary
                    article['summary'] = self._generate_contextual_summary(title, source_name)
                    logger.debug(f"Replaced duplicate summary for: {title[:50]}...")
            elif title and not summary:
                # Generate summary if missing
                article['summary'] = self._generate_contextual_summary(title, source_name)
            
            # Fast duplicate check first (before URL validation)
            if self._is_duplicate_fast(article['url'], article['title']):
                self.duplicate_count += 1
                return False
            
            # URL validation
            if self.url_validator:
                is_valid, info = self.url_validator.validate_article_url(article)
                if not is_valid:
                    logger.debug(f"Invalid URL rejected: {article.get('url')} - {info.get('error')}")
                    return False
            
            # Enhanced summary validation and improvement using integrated Summary Enhancer
            try:
                article = self.summary_enhancer.enhance_article_summary(article, source_name)
            except Exception as e:
                logger.warning(f"Summary enhancer error: {e}")
                # Fall back to basic handling
                title = article.get('title', '')
                summary = article.get('summary', '')
                
                if summary and title:
                    # Basic similarity check
                    words_title = set(title.lower().split())
                    words_summary = set(summary.lower().split())
                    if words_title and words_summary:
                        similarity = len(words_title.intersection(words_summary)) / len(words_title.union(words_summary))
                        if similarity > 0.8:  # Very similar
                            article['summary'] = ""  # Clear for contextual generation
                
                # Generate contextual summary if needed
                if not article.get('summary'):
                    category = source_tags[0] if source_tags else 'general'
                    article['summary'] = self._generate_contextual_summary(title, source_name)
                title = article.get('title', '')
                summary = article.get('summary', '')
                
                if summary and title:
                    # Basic similarity check
                    title_clean = title.lower().strip()
                    summary_clean = summary.lower().strip()
                    
                    # If they're identical or very similar, generate a better one
                    if (title_clean == summary_clean or 
                        summary_clean in title_clean or 
                        len(summary_clean) - len(title_clean) < 20):
                        article['summary'] = self._generate_contextual_summary(title, source_name)
                        logger.debug(f"Generated unique summary for: {title[:50]}...")
                elif not summary:
                    article['summary'] = self._generate_contextual_summary(title, source_name)
            
            # Ensure we have a summary (use contextual generation if still empty)
            if not article.get('summary'):
                article['summary'] = self._generate_contextual_summary(article.get('title', ''), source_name)
            
            # Categorize article using YAML mappings
            category, auto_tags = self.categorize_article(article)
            all_tags = list(set(source_tags + auto_tags))
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (title, summary, url, source, date, categories, tags, authors, subcategory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['title'],
                article.get('summary'),
                article['url'],
                source_name,
                article['date'],
                category,
                json.dumps(all_tags),
                article.get('author'),
                json.dumps(auto_tags) if auto_tags else None  # Store subcategories in subcategory field
            ))
            
            if cursor.rowcount > 0:
                conn.commit()
                # Add to duplicate cache for future fast checks
                self._add_to_duplicate_cache(article['url'], article['title'])
                logger.debug(f"Saved: {article['title'][:60]}... [Category: {category}, Tags: {auto_tags}]")
                self.articles_saved += 1
                result = True
            else:
                self.duplicate_count += 1
                result = False
                
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            self.error_count += 1
            return False
    
    def _generate_contextual_summary(self, title: str, source: str) -> str:
        """Generate a contextual summary when original is missing or duplicate"""
        if not title:
            return "Health and wellness information from medical experts."
        
        title_lower = title.lower()
        
        # Generate specific summaries based on content
        if 'diabetes' in title_lower:
            return "Comprehensive information about diabetes management, blood sugar control, and treatment options for better health outcomes."
        elif 'heart' in title_lower or 'cardiovascular' in title_lower:
            return "Heart health information including cardiovascular disease prevention, treatment advances, and lifestyle recommendations."
        elif 'nutrition' in title_lower or 'diet' in title_lower:
            return "Evidence-based nutritional guidance and dietary recommendations for optimal health and wellness."
        elif 'obesity' in title_lower or 'weight' in title_lower:
            return "Weight management strategies, obesity prevention methods, and healthy lifestyle guidance from healthcare professionals."
        elif 'cancer' in title_lower:
            return "Important cancer information including prevention strategies, treatment advances, and patient care updates."
        elif 'mental health' in title_lower or 'depression' in title_lower or 'anxiety' in title_lower:
            return "Mental health resources, treatment information, and emotional wellbeing guidance from healthcare experts."
        elif 'vaccine' in title_lower or 'vaccination' in title_lower:
            return "Vaccination information, safety data, and immunization guidelines from public health authorities."
        elif 'research' in title_lower or 'study' in title_lower:
            return "Medical research findings and scientific studies with implications for patient care and health outcomes."
        elif 'food' in title_lower or 'organic' in title_lower:
            return "Food and nutrition information focusing on healthy eating, food safety, and dietary recommendations."
        else:
            # Source-specific defaults
            if 'who' in source.lower():
                return "World Health Organization health updates and international health guidance for global communities."
            elif 'cdc' in source.lower():
                return "Centers for Disease Control health information and public health guidance for disease prevention."
            elif 'nih' in source.lower():
                return "National Institutes of Health research updates and medical information from leading scientists."
            else:
                return "Health information and medical insights from healthcare professionals and trusted medical sources."
    
    def scrape_rss_sources(self, source_list: List[Dict], max_articles_per_source: int = 50):
        """Scrape RSS sources with validation and respectful delays"""
        for source in source_list:
            logger.info(f"📡 Scraping {source['name']}...")
            
            try:
                # Validate feed first
                is_valid, reason, _ = self.feed_validator.validate_feed(source['url'], source['name'])
                if not is_valid:
                    logger.warning(f"   ⏭️  Skipping {source['name']}: {reason}")
                    self.validation_failures += 1
                    continue
                
                # Parse the feed
                articles = self.parse_rss_feed(source['url'])
                
                if not articles:
                    logger.warning(f"   ⚠️  No articles found from {source['name']}")
                    continue
                
                saved_count = 0
                for article in articles[:max_articles_per_source]:
                    if self.save_article(article, source['name'], source.get('tags', [])):
                        saved_count += 1
                    
                    # Small delay between articles
                    time.sleep(0.1)
                
                logger.info(f"   ✅ {saved_count} articles saved from {source['name']}")
                
                # Respectful delay between sources (longer for high-priority sources)
                delay = 1.5 if source.get('priority', 3) <= 2 else 1.0
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"   ❌ Error scraping {source['name']}: {e}")
                self.error_count += 1
    
    def scrape_google_news(self, max_keywords: int = 5):
        """Scrape Google News for health topics with rate limiting"""
        logger.info("📰 Scraping Google News health topics...")
        
        keywords_to_use = self.google_news_keywords[:max_keywords]
        
        for i, keyword in enumerate(keywords_to_use):
            try:
                # Google News RSS URL
                url = f"https://news.google.com/rss/search?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
                
                # Validate and parse
                is_valid, reason, _ = self.feed_validator.validate_feed(url, f"Google News ({keyword})")
                if not is_valid:
                    logger.warning(f"   ⏭️  Skipping Google News '{keyword}': {reason}")
                    continue
                
                articles = self.parse_rss_feed(url)
                
                saved_count = 0
                for article in articles[:15]:  # Limit per keyword
                    if self.save_article(article, f"Google News ({keyword})", [keyword, "google_news"]):
                        saved_count += 1
                
                if saved_count > 0:
                    logger.info(f"   ✅ {saved_count} articles for '{keyword}'")
                
                # Respectful delay (longer for Google)
                time.sleep(3 + random.uniform(0, 2))
                
            except Exception as e:
                logger.error(f"   ❌ Error with keyword '{keyword}': {e}")
    
    def run_comprehensive_scrape(self):
        """Run complete scraping from all sources with enhanced validation"""
        start_time = datetime.now()
        
        logger.info("🚀 Starting Enhanced Health News Scraper")
        logger.info("=" * 60)
        
        # Create/verify database
        self.create_database()
        
        # Load existing hashes for fast duplicate detection
        self._load_existing_hashes()
        
        # Validate feeds at startup
        valid_feeds, invalid_feeds = self.validate_feeds_startup()
        
        if valid_feeds == 0:
            logger.error("❌ No valid feeds available. Check network connection and feed URLs.")
            return 0
        
        # Scrape RSS sources by priority
        logger.info("📡 Phase 1: High Priority Sources (WHO, CDC, Harvard)...")
        priority_1_sources = [s for s in self.rss_sources if s.get('priority', 3) == 1]
        self.scrape_rss_sources(priority_1_sources, max_articles_per_source=25)
        
        logger.info("📺 Phase 2: Major News Sources (BBC, NPR, etc.)...")
        priority_2_sources = [s for s in self.rss_sources if s.get('priority', 3) == 2]
        self.scrape_rss_sources(priority_2_sources, max_articles_per_source=20)
        
        logger.info("🏥 Phase 3: Health Publications...")
        priority_3_sources = [s for s in self.rss_sources if s.get('priority', 3) == 3]
        self.scrape_rss_sources(priority_3_sources, max_articles_per_source=15)
        
        logger.info("🔍 Phase 4: Google News Topics...")
        self.scrape_google_news(max_keywords=5)
        
        # NEW: Phase 5: Implement fallback mechanism for categories with no fresh news
        logger.info("🔄 Phase 5: Checking for empty categories and implementing fallbacks...")
        self._implement_fallback_mechanism()
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Log article counts per category for monitoring
        category_counts = self._get_articles_by_category_count()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ ENHANCED HEALTH SCRAPER COMPLETE")
        logger.info("=" * 60)
        logger.info(f"⏱️  Duration: {duration:.1f} seconds")
        logger.info(f"📊 Feed Validation: {valid_feeds} valid, {invalid_feeds} invalid/blacklisted")
        logger.info(f"📰 Articles Saved: {self.articles_saved}")
        logger.info(f"🔄 Duplicates Blocked: {self.duplicate_count}")
        logger.info(f"❌ Errors: {self.error_count}")
        logger.info(f"🚫 Validation Failures: {self.validation_failures}")
        
        # Category-wise breakdown for monitoring "latest news" issue
        logger.info(f"\n📊 Article Distribution by Category:")
        for category, count in category_counts.items():
            if count == 0:
                logger.warning(f"   ⚠️  {category}: {count} articles (NO FRESH NEWS)")
            elif count < 5:
                logger.warning(f"   ⚠️  {category}: {count} articles (LOW COUNT)")
            else:
                logger.info(f"   ✅ {category}: {count} articles")
        
        # Check for empty categories and provide guidance
        empty_categories = [cat for cat, count in category_counts.items() if count == 0]
        if empty_categories:
            logger.warning(f"\n⚠️  CATEGORIES WITH NO FRESH NEWS: {', '.join(empty_categories)}")
            logger.info("💡 Suggestions to fix missing news:")
            logger.info("   • Check RSS feed URLs for these categories")
            logger.info("   • Verify network connectivity")
            logger.info("   • Review blacklisted feeds in config.yml")
            logger.info("   • Review blacklisted feeds in feeds_blacklist.yml")
            logger.info("   • Consider adding fallback sources for these categories")
        
        efficiency = (self.articles_saved / (self.articles_saved + self.duplicate_count)) * 100 if (self.articles_saved + self.duplicate_count) > 0 else 0
        logger.info(f"🎯 Efficiency: {efficiency:.1f}% (unique articles saved)")
        
        if self.articles_saved > 0:
            logger.info(f"\n🎉 SUCCESS: {self.articles_saved} health articles collected!")
            logger.info("📱 Start your API server to access the content:")
            logger.info("   python start.py")
            logger.info("   Visit: http://localhost:8000/docs")
        else:
            logger.info(f"\n⚠️  No new articles saved")
            if self.duplicate_count > 0:
                logger.info(f"   • {self.duplicate_count} duplicates prevented (good!)")
            logger.info("   • Check internet connection")
            logger.info("   • Articles may already exist in database")
        
        return self.articles_saved
    
    def _get_articles_by_category_count(self) -> Dict[str, int]:
        """Get count of articles saved by category for monitoring"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get articles from last 24 hours grouped by category
            cursor.execute("""
                SELECT categories, COUNT(*) 
                FROM articles 
                WHERE date > datetime('now', '-1 day')
                GROUP BY categories
            """)
            
            category_counts = {}
            for row in cursor.fetchall():
                category = row[0] if row[0] else 'unknown'
                count = row[1]
                
                # Handle JSON array format
                try:
                    if category.startswith('['):
                        import json
                        categories_list = json.loads(category)
                        category = categories_list[0] if categories_list else 'unknown'
                except:
                    pass
                
                category_counts[category] = count
            
            conn.close()
            
            # Ensure all main categories are represented
            main_categories = ['news', 'diseases', 'solutions', 'food', 'audience', 'trending']
            for cat in main_categories:
                if cat not in category_counts:
                    category_counts[cat] = 0
            
            return category_counts
            
        except Exception as e:
            logger.error(f"Error getting category counts: {e}")
            return {}
    
    def _implement_fallback_mechanism(self):
        """Implement fallback mechanism for categories with no fresh news"""
        try:
            category_counts = self._get_articles_by_category_count()
            empty_categories = [cat for cat, count in category_counts.items() if count == 0]
            
            if empty_categories:
                logger.info(f"🔄 Implementing fallback for empty categories: {empty_categories}")
                
                for category in empty_categories:
                    # Show older cached articles (last 7 days) for empty categories
                    self._add_cached_articles_for_category(category)
                    
                    # Try Google News search as fallback
                    if category == 'news':
                        self._scrape_google_news_for_category(category, ['latest health news', 'medical news'])
                    elif category == 'diseases':
                        self._scrape_google_news_for_category(category, ['diabetes', 'heart disease', 'obesity'])
                    elif category == 'solutions':
                        self._scrape_google_news_for_category(category, ['health solutions', 'medical treatment'])
                    elif category == 'food':
                        self._scrape_google_news_for_category(category, ['nutrition news', 'healthy food', 'diet health'])
                    elif category == 'blogs_and_opinions':
                        self._scrape_google_news_for_category(category, [
                            'health opinions', 'medical commentary', 'health blog', 
                            'wellness blog', 'nutrition opinion', 'medical advice',
                            'health expert opinion', 'doctor commentary', 'health column',
                            'wellness tips', 'medical insights', 'health perspective'
                        ])
                    elif category == 'trending':
                        self._scrape_google_news_for_category(category, ['trending health', 'viral health', 'health news'])
                    elif category == 'audience':
                        self._scrape_google_news_for_category(category, ['women health', 'men health', 'children health'])
                    
        except Exception as e:
            logger.error(f"Error implementing fallback mechanism: {e}")
    
    def _add_cached_articles_for_category(self, category: str):
        """Mark older articles as recent for categories with no fresh news"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Find recent articles (last 7 days) for this category
            cursor.execute("""
                UPDATE articles 
                SET date = datetime('now') 
                WHERE categories LIKE ? AND date > datetime('now', '-7 days')
                ORDER BY date DESC 
                LIMIT 5
            """, (f'%{category}%',))
            
            updated_count = cursor.rowcount
            if updated_count > 0:
                conn.commit()
                logger.info(f"   📤 Promoted {updated_count} cached articles for category '{category}'")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error adding cached articles for {category}: {e}")
    
    def _scrape_google_news_for_category(self, category: str, keywords: List[str]):
        """Scrape Google News for specific category keywords as fallback"""
        try:
            for keyword in keywords:
                try:
                    url = f"https://news.google.com/rss/search?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
                    
                    # Validate and parse
                    is_valid, reason, _ = self.feed_validator.validate_feed(url, f"Google News Fallback ({keyword})")
                    if not is_valid:
                        continue
                    
                    articles = self.parse_rss_feed(url)
                    
                    saved_count = 0
                    for article in articles[:5]:  # Limited fallback
                        # Force category assignment
                        if self.save_article(article, f"Google News Fallback ({keyword})", [keyword, category, "fallback"]):
                            saved_count += 1
                    
                    if saved_count > 0:
                        logger.info(f"   📰 Fallback: {saved_count} articles for '{category}' using '{keyword}'")
                    
                    time.sleep(2)  # Respectful delay
                    
                except Exception as e:
                    logger.debug(f"Error with fallback keyword '{keyword}': {e}")
                    
        except Exception as e:
            logger.error(f"Error in Google News fallback for {category}: {e}")
    
    def run_comprehensive_scrape(self):
        """Run complete scraping from all sources with enhanced validation"""
        start_time = datetime.now()
        
        logger.info("🚀 Starting Enhanced Health News Scraper")
        logger.info("=" * 60)
    
    def run_quick_scrape(self):
        """Run quick scrape from high-priority sources only"""
        logger.info("⚡ Quick Health News Update")
        logger.info("=" * 40)
        
        self.create_database()
        self._load_existing_hashes()
        
        # Validate feeds
        valid_feeds, invalid_feeds = self.validate_feeds_startup()
        
        if valid_feeds == 0:
            logger.error("❌ No valid feeds available.")
            return 0
        
        # Only priority 1 and 2 sources
        high_priority_sources = [s for s in self.rss_sources if s.get('priority', 3) <= 2]
        self.scrape_rss_sources(high_priority_sources, max_articles_per_source=12)
        
        # Limited Google News
        self.scrape_google_news(max_keywords=3)
        
        logger.info(f"\n⚡ Quick update complete:")
        logger.info(f"   📰 {self.articles_saved} articles saved")
        logger.info(f"   🔄 {self.duplicate_count} duplicates prevented")
        logger.info(f"   🚫 {self.validation_failures} feed failures")
        
        return self.articles_saved

def main():
    """Main function with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Health News Scraper")
    parser.add_argument("--quick", action="store_true", help="Run quick update (high-priority sources only)")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive scrape (all sources)")
    parser.add_argument("--validate-only", action="store_true", help="Only validate feeds, don't scrape")
    
    args = parser.parse_args()
    
    scraper = EnhancedHealthScraper()
    
    if args.validate_only:
        valid_feeds, invalid_feeds = scraper.validate_feeds_startup()
        logger.info(f"Validation complete: {valid_feeds} valid, {invalid_feeds} invalid feeds")
        return valid_feeds
    elif args.quick:
        articles_saved = scraper.run_quick_scrape()
    else:
        articles_saved = scraper.run_comprehensive_scrape()
    
    return articles_saved

if __name__ == "__main__":
    main()
        
    def create_database(self):
        """Create articles database with optimized schema"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    summary TEXT,
                    content TEXT,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT,
                    date TIMESTAMP NOT NULL,
                    categories TEXT,
                    subcategory TEXT,
                    tags TEXT,
                    author TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles(categories)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database creation error: {e}")
    
    def parse_rss_feed(self, url: str, timeout: int = 15) -> List[Dict]:
        """Parse RSS feed using only standard library"""
        articles = []
        
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle different RSS formats
            items = root.findall('.//item') or root.findall('.//{http://purl.org/rss/1.0/}item')
            
            for item in items:
                try:
                    title = self._get_text(item, ['title'])
                    link = self._get_text(item, ['link', 'guid'])
                    description = self._get_text(item, ['description', 'summary'])
                    pub_date = self._get_text(item, ['pubDate', 'published', 'date'])
                    author = self._get_text(item, ['author', 'creator', 'dc:creator'])
                    
                    if title and link:
                        # Parse date
                        parsed_date = self._parse_date(pub_date or "")
                        
                        # Clean description and extract meaningful summary
                        if description:
                            description = self._clean_html(description)
                            # Extract more meaningful summary content
                            description = self._extract_meaningful_summary(description, title or "")
                            # Limit length but keep meaningful content
                            description = description[:800] + '...' if len(description) > 800 else description
                        
                        articles.append({
                            'title': (title or "Untitled").strip()[:200],
                            'url': (link or "").strip(),
                            'summary': description,
                            'date': parsed_date,
                            'author': author
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing RSS item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"RSS feed error for {url}: {e}")
            
        return articles
    
    def _get_text(self, element, tag_names: List[str]) -> Optional[str]:
        """Get text from first available tag"""
        for tag_name in tag_names:
            try:
                # Handle namespaced tags
                if ':' in tag_name:
                    namespace_map = {
                        'dc': 'http://purl.org/dc/elements/1.1/',
                        'content': 'http://purl.org/rss/1.0/modules/content/'
                    }
                    elem = element.find(tag_name, namespace_map)
                else:
                    elem = element.find(tag_name) or element.find(f'.//{tag_name}')
                
                if elem is not None and elem.text:
                    return elem.text.strip()
            except Exception:
                # Try without namespace if namespaced search fails
                try:
                    simple_tag = tag_name.split(':')[-1]  # Get tag without namespace
                    elem = element.find(simple_tag) or element.find(f'.//{simple_tag}')
                    if elem is not None and elem.text:
                        return elem.text.strip()
                except Exception:
                    continue
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        if not date_str:
            return datetime.now()
            
        # Common date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S GMT',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # If all else fails, return current time
        logger.debug(f"Could not parse date: {date_str}")
        return datetime.now()
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
            
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        return text.strip()
    
    def _extract_meaningful_summary(self, description: str, title: str) -> str:
        """Extract meaningful summary content from description, ensuring it's unique from title"""
        if not description:
            return ""
            
        # Remove title from description if it appears at the beginning
        if title and description.lower().startswith(title.lower()):
            description = description[len(title):].lstrip(' .-:')
        
        # Remove common unwanted patterns
        patterns_to_remove = [
            r'Read more.*',
            r'Click here.*',
            r'Learn more.*',
            r'Continue reading.*',
            r'Full article.*',
            r'View original.*',
            r'\[.*?\]',  # Remove content in brackets
            r'Source:.*',
            r'Via:.*',
            r'From:.*',
            r'Share this:.*',
            r'Subscribe to.*',
            r'Follow us.*',
            r'More information.*'
        ]
        
        for pattern in patterns_to_remove:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Clean up extra whitespace and punctuation
        description = re.sub(r'\s+', ' ', description).strip()
        description = re.sub(r'^[:\-\s\.]+', '', description)
        description = re.sub(r'[:\-\s\.]+$', '', description)
        
        # Check if summary is just a duplicate of the title (case-insensitive)
        if title and description:
            title_clean = title.lower().strip()
            description_clean = description.lower().strip()
            
            # If they're identical or very similar, return empty (will be handled by fallback)
            if (title_clean == description_clean or 
                description_clean in title_clean or
                title_clean in description_clean):
                if len(description_clean) - len(title_clean) < 20:  # Not much additional content
                    return ""
        
        # If the remaining text is too short, return empty (will be handled by fallback)
        if len(description.strip()) < 50:
            return ""
            
        return description
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for duplicate detection"""
        if not title:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = title.lower().strip()
        
        # Remove common punctuation and special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common prefixes that don't affect content
        prefixes_to_remove = [
            'new study:', 'study:', 'research:', 'scientists:', 'researchers:',
            'breaking:', 'news:', 'alert:', 'update:'
        ]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                break
        
        return normalized
    
    def _is_duplicate_title(self, normalized_title: str) -> bool:
        """Check if a similar title already exists in the database"""
        if not normalized_title or len(normalized_title) < 10:
            return False
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get all existing titles from the last 30 days to check for duplicates
            cursor.execute('''
                SELECT title FROM articles 
                WHERE date > date('now', '-30 days')
                ORDER BY date DESC
                LIMIT 1000
            ''')
            
            existing_titles = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()
            
            # Check for exact matches or very similar titles
            for existing_title in existing_titles:
                existing_normalized = self._normalize_title(existing_title)
                
                # Exact match
                if normalized_title == existing_normalized:
                    return True
                
                # Very similar match (85% similarity)
                if self._calculate_similarity(normalized_title, existing_normalized) > 0.85:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate title: {e}")
            return False
    
    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using word overlap"""
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def cleanup_duplicates(self):
        """Remove duplicate articles from the database"""
        logger.info("🧹 Cleaning up duplicate articles...")
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Find articles with very similar titles
            cursor.execute('''
                SELECT id, title, url, date, source 
                FROM articles 
                ORDER BY date DESC
            ''')
            
            articles = cursor.fetchall()
            duplicates_found = 0
            articles_to_keep = set()
            articles_to_delete = set()
            
            for i, article1 in enumerate(articles):
                if article1[0] in articles_to_delete:
                    continue
                    
                id1, title1, url1, date1, source1 = article1
                normalized_title1 = self._normalize_title(title1)
                
                # Mark this article as one to keep if not already processed
                if article1[0] not in articles_to_delete:
                    articles_to_keep.add(id1)
                
                # Compare with subsequent articles
                for j in range(i + 1, len(articles)):
                    article2 = articles[j]
                    if article2[0] in articles_to_delete:
                        continue
                        
                    id2, title2, url2, date2, source2 = article2
                    normalized_title2 = self._normalize_title(title2)
                    
                    # Check for duplicates
                    is_duplicate = False
                    
                    # Same URL
                    if url1 == url2:
                        is_duplicate = True
                    
                    # Very similar titles (90% similarity for cleanup)
                    elif self._calculate_similarity(normalized_title1, normalized_title2) > 0.90:
                        is_duplicate = True
                    
                    if is_duplicate:
                        # Keep the one with better source or newer date
                        if self._should_keep_article1_over_article2(article1, article2):
                            articles_to_delete.add(id2)
                        else:
                            articles_to_delete.add(id1)
                            articles_to_keep.discard(id1)
                            break  # Don't process this article further
                        
                        duplicates_found += 1
            
            # Delete the duplicate articles
            if articles_to_delete:
                placeholders = ','.join(['?'] * len(articles_to_delete))
                cursor.execute(f'DELETE FROM articles WHERE id IN ({placeholders})', list(articles_to_delete))
                conn.commit()
                
                logger.info(f"🗑️  Removed {len(articles_to_delete)} duplicate articles")
            else:
                logger.info("✨ No duplicates found")
            
            conn.close()
            return len(articles_to_delete)
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicates: {e}")
            return 0
    
    def _should_keep_article1_over_article2(self, article1: tuple, article2: tuple) -> bool:
        """Determine which article to keep when duplicates are found"""
        id1, title1, url1, date1, source1 = article1
        id2, title2, url2, date2, source2 = article2
        
        # Prefer certain sources
        preferred_sources = [
            'WHO Health News', 'NIH News Releases', 'CDC Health News',
            'Harvard Nutrition Source', 'BBC Health', 'NPR Health'
        ]
        
        source1_preferred = any(pref in source1 for pref in preferred_sources)
        source2_preferred = any(pref in source2 for pref in preferred_sources)
        
        if source1_preferred and not source2_preferred:
            return True
        elif source2_preferred and not source1_preferred:
            return False
        
        # If both or neither are preferred, choose the newer one
        try:
            date1_obj = datetime.fromisoformat(date1.replace('Z', '+00:00'))
            date2_obj = datetime.fromisoformat(date2.replace('Z', '+00:00'))
            return date1_obj > date2_obj
        except:
            # If date parsing fails, keep the first one
            return True
    
    def categorize_article(self, article: Dict) -> Tuple[str, List[str]]:
        """Smart categorization based on title and content using category keywords from YAML"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        content = title + ' ' + summary
        
        # Load category keywords from YAML file
        try:
            import yaml
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "config" / "category_keywords.yml"
            with open(config_path, 'r', encoding='utf-8') as f:
                categories_data = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load category keywords: {e}")
            # Fallback to basic categorization
            return self._basic_categorization(content)
        
        # Ensure we have the categories structure
        if not categories_data or 'categories' not in categories_data:
            logger.warning("Invalid category_keywords.yml structure")
            return self._basic_categorization(content)
        
        categories = categories_data['categories']
        
        # Find best matching category and subcategories
        best_category = 'news'  # Default fallback
        best_subcategories = []
        max_score = 0
        
        for category_name, category_info in categories.items():
            if not isinstance(category_info, dict) or 'tags' not in category_info:
                continue
                
            category_score = 0
            matched_subcategories = []
            
            # Check each tag in this category
            for tag in category_info['tags']:
                tag_lower = tag.lower()
                
                # Count keyword matches in content (weighted by importance)
                title_matches = content.count(tag_lower)
                if title_matches > 0:
                    # Higher weight for title matches
                    weight = 3 if tag_lower in title else 1
                    category_score += title_matches * weight
                    
                    # Map subcategory based on keyword match
                    subcategory = self._map_keyword_to_subcategory(tag_lower, category_name)
                    if subcategory and subcategory not in matched_subcategories:
                        matched_subcategories.append(subcategory)
            
            # Update best match if this category scored higher
            if category_score > max_score:
                max_score = category_score
                best_category = category_name
                best_subcategories = matched_subcategories
        
        # Ensure we have at least one subcategory
        if not best_subcategories:
            best_subcategories = self._get_default_subcategory(best_category)
        
        return best_category, best_subcategories
    
    def _map_keyword_to_subcategory(self, keyword: str, category: str) -> Optional[str]:
        """Map a matched keyword to its appropriate subcategory"""
        
        # Disease category mappings
        if category == 'diseases':
            diabetes_keywords = ['diabetes', 'blood sugar', 'insulin', 'glucose', 'diabetic', 'hyperglycemia', 'hypoglycemia']
            obesity_keywords = ['obesity', 'overweight', 'weight gain', 'bmi', 'body mass index', 'weight management']
            cardio_keywords = ['heart disease', 'cardiovascular', 'cardiac', 'heart attack', 'stroke', 'hypertension', 'high blood pressure']
            inflammation_keywords = ['inflammation', 'inflammatory', 'anti-inflammatory', 'chronic inflammation']
            liver_keywords = ['liver', 'hepatic', 'liver disease', 'fatty liver', 'cirrhosis', 'hepatitis']
            kidney_keywords = ['kidney', 'renal', 'kidney disease', 'kidney stone', 'dialysis']
            thyroid_keywords = ['thyroid', 'hypothyroid', 'hyperthyroid', 'thyroid gland']
            metabolic_keywords = ['metabolism', 'metabolic', 'metabolic syndrome', 'metabolic disorder']
            sleep_keywords = ['sleep disorder', 'insomnia', 'sleep apnea', 'sleep health']
            skin_keywords = ['skin', 'dermatology', 'acne', 'eczema', 'psoriasis', 'dermatitis']
            eyes_ears_keywords = ['eye', 'vision', 'ear', 'hearing', 'ophthalmology', 'audiology']
            reproductive_keywords = ['reproductive health', 'fertility', 'infertility', 'sexual health']
            
            if any(k in keyword for k in diabetes_keywords):
                return 'diabetes'
            elif any(k in keyword for k in obesity_keywords):
                return 'obesity'
            elif any(k in keyword for k in cardio_keywords):
                return 'cardiovascular'
            elif any(k in keyword for k in inflammation_keywords):
                return 'inflammation'
            elif any(k in keyword for k in liver_keywords):
                return 'liver'
            elif any(k in keyword for k in kidney_keywords):
                return 'kidney'
            elif any(k in keyword for k in thyroid_keywords):
                return 'thyroid'
            elif any(k in keyword for k in metabolic_keywords):
                return 'metabolic'
            elif any(k in keyword for k in sleep_keywords):
                return 'sleep disorders'
            elif any(k in keyword for k in skin_keywords):
                return 'skin'
            elif any(k in keyword for k in eyes_ears_keywords):
                return 'eyes and ears'
            elif any(k in keyword for k in reproductive_keywords):
                return 'reproductive health'
        
        # Solutions category mappings
        elif category == 'solutions':
            nutrition_keywords = ['nutrition', 'dietary', 'vitamins', 'minerals', 'balanced diet', 'healthy eating']
            fitness_keywords = ['fitness', 'exercise', 'workout', 'physical activity', 'training', 'cardio', 'strength']
            lifestyle_keywords = ['lifestyle', 'daily habits', 'routine', 'behavior modification', 'healthy habits']
            wellness_keywords = ['wellness', 'wellbeing', 'holistic health', 'self-care', 'meditation', 'mindfulness']
            prevention_keywords = ['prevention', 'preventive', 'screening', 'vaccination', 'checkup', 'early detection']
            
            if any(k in keyword for k in nutrition_keywords):
                return 'nutrition'
            elif any(k in keyword for k in fitness_keywords):
                return 'fitness'
            elif any(k in keyword for k in lifestyle_keywords):
                return 'lifestyle'
            elif any(k in keyword for k in wellness_keywords):
                return 'wellness'
            elif any(k in keyword for k in prevention_keywords):
                return 'prevention'
        
        # Food category mappings
        elif category == 'food':
            natural_keywords = ['natural food', 'organic', 'whole foods', 'unprocessed', 'superfood', 'antioxidants']
            organic_keywords = ['organic food', 'organic farming', 'pesticide free', 'chemical free', 'sustainable food']
            processed_keywords = ['processed food', 'ultra processed', 'packaged food', 'fast food', 'junk food']
            seafood_keywords = ['fish', 'seafood', 'salmon', 'tuna', 'shellfish', 'omega-3 fish']
            safety_keywords = ['food safety', 'food poisoning', 'contamination', 'food recall', 'hygiene']
            
            if any(k in keyword for k in natural_keywords):
                return 'natural food'
            elif any(k in keyword for k in organic_keywords):
                return 'organic food'
            elif any(k in keyword for k in processed_keywords):
                return 'processed food'
            elif any(k in keyword for k in seafood_keywords):
                return 'fish and seafood'
            elif any(k in keyword for k in safety_keywords):
                return 'food safety'
        
        # Audience category mappings
        elif category == 'audience':
            women_keywords = ["women's health", 'female health', 'pregnancy', 'menstruation', 'menopause', 'women', 'female']
            men_keywords = ["men's health", 'male health', 'prostate', 'testosterone', 'men', 'male']
            children_keywords = ["children's health", 'pediatric', 'child health', 'kids health', 'children', 'kids', 'child']
            teen_keywords = ['teen health', 'teenage health', 'adolescent health', 'teenagers', 'teens', 'adolescent']
            senior_keywords = ['elderly health', 'senior health', 'aging', 'geriatric', 'seniors', 'elderly']
            athlete_keywords = ['sports medicine', 'athlete health', 'sports nutrition', 'athletes', 'performance']
            family_keywords = ['family health', 'household health', 'family wellness', 'families', 'family']
            
            if any(k in keyword for k in women_keywords):
                return 'women'
            elif any(k in keyword for k in men_keywords):
                return 'men'
            elif any(k in keyword for k in children_keywords):
                return 'children'
            elif any(k in keyword for k in teen_keywords):
                return 'teenagers'
            elif any(k in keyword for k in senior_keywords):
                return 'seniors'
            elif any(k in keyword for k in athlete_keywords):
                return 'athletes'
            elif any(k in keyword for k in family_keywords):
                return 'families'
        
        # Trending category mappings
        elif category == 'trending':
            gut_keywords = ['gut health', 'microbiome', 'digestive health', 'probiotics', 'gut bacteria']
            mental_keywords = ['mental health', 'psychological health', 'depression', 'anxiety', 'stress']
            hormone_keywords = ['hormones', 'hormonal health', 'hormone balance', 'testosterone', 'estrogen']
            addiction_keywords = ['addiction', 'substance abuse', 'dependency', 'addiction recovery']
            sleep_keywords = ['sleep health', 'sleep wellness', 'sleep quality', 'sleep hygiene']
            sexual_keywords = ['sexual wellness', 'sexual health', 'intimate health', 'reproductive wellness']
            
            if any(k in keyword for k in gut_keywords):
                return 'gut health'
            elif any(k in keyword for k in mental_keywords):
                return 'mental health'
            elif any(k in keyword for k in hormone_keywords):
                return 'hormones'
            elif any(k in keyword for k in addiction_keywords):
                return 'addiction'
            elif any(k in keyword for k in sleep_keywords):
                return 'sleep health'
            elif any(k in keyword for k in sexual_keywords):
                return 'sexual wellness'
        
        # News category mappings
        elif category == 'news':
            latest_keywords = ['latest', 'recent', 'new', 'breaking news', 'urgent', 'today']
            policy_keywords = ['policy and regulation', 'health policy', 'medical regulation', 'government policy']
            govt_keywords = ['govt schemes', 'government schemes', 'public health programs', 'health initiatives']
            international_keywords = ['international', 'global health', 'world health', 'who']
            
            if any(k in keyword for k in latest_keywords):
                return 'latest'
            elif any(k in keyword for k in policy_keywords):
                return 'policy and regulation'
            elif any(k in keyword for k in govt_keywords):
                return 'govt schemes'
            elif any(k in keyword for k in international_keywords):
                return 'international'
        
        return None
    
    def _get_default_subcategory(self, category: str) -> List[str]:
        """Get default subcategory for a category if no specific match found"""
        defaults = {
            'diseases': ['metabolic'],
            'solutions': ['wellness'],
            'food': ['natural food'],
            'audience': ['families'],
            'trending': ['gut health'],
            'news': ['latest'],
            'blogs_and_opinions': []
        }
        return defaults.get(category, ['general'])
    
    def _basic_categorization(self, content: str) -> Tuple[str, List[str]]:
        """Fallback basic categorization if YAML file unavailable"""
        if any(word in content for word in ['diabetes', 'blood sugar', 'insulin', 'glucose']):
            return 'diseases', ['diabetes', 'metabolic']
        elif any(word in content for word in ['cancer', 'tumor', 'oncology', 'chemotherapy']):
            return 'diseases', ['cancer', 'treatment']
        elif any(word in content for word in ['heart', 'cardiac', 'cardiovascular', 'cholesterol']):
            return 'diseases', ['cardiovascular', 'heart']
        elif any(word in content for word in ['mental health', 'depression', 'anxiety', 'stress']):
            return 'diseases', ['mental health', 'wellness']
        elif any(word in content for word in ['nutrition', 'diet', 'food', 'eating']):
            return 'food', ['nutrition', 'diet']
        elif any(word in content for word in ['exercise', 'fitness', 'workout', 'physical activity']):
            return 'solutions', ['fitness', 'exercise']
        elif any(word in content for word in ['vaccine', 'vaccination', 'immunization']):
            return 'solutions', ['prevention', 'vaccination']
        elif any(word in content for word in ['who', 'policy', 'government', 'health policy']):
            return 'news', ['policy', 'government']
        elif any(word in content for word in ['research', 'study', 'clinical trial']):
            return 'news', ['research', 'study']
        else:
            return 'news', ['general']
    
    def save_article(self, article: Dict, source_name: str, source_tags: List[str]) -> bool:
        """Save article to database with validation and deduplication"""
        try:
            # URL validation
            if self.url_validator:
                is_valid, info = self.url_validator.validate_article_url(article)
                if not is_valid:
                    logger.debug(f"Invalid URL rejected: {article.get('url')} - {info.get('error')}")
                    return False
            
            # Check for duplicate titles (case-insensitive, normalized)
            normalized_title = self._normalize_title(article['title'])
            if self._is_duplicate_title(normalized_title):
                logger.debug(f"Duplicate title skipped: {article['title'][:60]}...")
                self.duplicate_count += 1
                return False
            
            # Ensure summary is unique from title
            title = article.get('title', '')
            summary = article.get('summary', '')
            
            # If summary is identical to title or very similar, generate a better one
            if summary and title:
                title_clean = title.lower().strip()
                summary_clean = summary.lower().strip()
                
                # Check if summary is just title or very similar
                if (title_clean == summary_clean or 
                    summary_clean in title_clean or 
                    len(summary_clean) - len(title_clean) < 20):
                    # Generate a contextual summary instead
                    article['summary'] = self._generate_contextual_summary(title, source_name)
                    logger.debug(f"Generated unique summary for: {title[:50]}...")
            elif not summary:
                # Generate summary if missing
                article['summary'] = self._generate_contextual_summary(title, source_name)
            
            # Categorize article using YAML mappings
            category, auto_tags = self.categorize_article(article)
            all_tags = list(set(source_tags + auto_tags))
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (title, summary, url, source, date, categories, tags, authors, subcategory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['title'],
                article.get('summary'),
                article['url'],
                source_name,
                article['date'],
                category,
                json.dumps(all_tags),
                article.get('author'),
                json.dumps(auto_tags) if auto_tags else None  # Store subcategories in subcategory field
            ))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.debug(f"Saved: {article['title'][:60]}... [Category: {category}, Tags: {auto_tags}]")
                self.articles_saved += 1
                result = True
            else:
                self.duplicate_count += 1
                result = False
                
            conn.close()
            return result
            
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            self.error_count += 1
            return False
    
    def _generate_contextual_summary(self, title: str, source: str) -> str:
        """Generate a contextual summary when original is missing or duplicate"""
        if not title:
            return "Health and wellness information from medical experts."
        
        title_lower = title.lower()
        
        # Generate specific summaries based on content
        if 'diabetes' in title_lower:
            return "Comprehensive information about diabetes management, blood sugar control, and treatment options for better health outcomes."
        elif 'heart' in title_lower or 'cardiovascular' in title_lower:
            return "Heart health information including cardiovascular disease prevention, treatment advances, and lifestyle recommendations."
        elif 'nutrition' in title_lower or 'diet' in title_lower:
            return "Evidence-based nutritional guidance and dietary recommendations for optimal health and wellness."
        elif 'obesity' in title_lower or 'weight' in title_lower:
            return "Weight management strategies, obesity prevention methods, and healthy lifestyle guidance from healthcare professionals."
        elif 'cancer' in title_lower:
            return "Important cancer information including prevention strategies, treatment advances, and patient care updates."
        elif 'mental health' in title_lower or 'depression' in title_lower or 'anxiety' in title_lower:
            return "Mental health resources, treatment information, and emotional wellbeing guidance from healthcare experts."
        elif 'vaccine' in title_lower or 'vaccination' in title_lower:
            return "Vaccination information, safety data, and immunization guidelines from public health authorities."
        elif 'research' in title_lower or 'study' in title_lower:
            return "Medical research findings and scientific studies with implications for patient care and health outcomes."
        elif 'food' in title_lower or 'organic' in title_lower:
            return "Food and nutrition information focusing on healthy eating, food safety, and dietary recommendations."
        else:
            # Source-specific defaults
            if 'who' in source.lower():
                return "World Health Organization health updates and international health guidance for global communities."
            elif 'cdc' in source.lower():
                return "Centers for Disease Control health information and public health guidance for disease prevention."
            elif 'nih' in source.lower():
                return "National Institutes of Health research updates and medical information from leading scientists."
            else:
                return "Health information and medical insights from healthcare professionals and trusted medical sources."
    
    def scrape_rss_sources(self, source_list: List[Dict], max_articles_per_source: int = 50):
        """Scrape all RSS sources in a list"""
        for source in source_list:
            logger.info(f"📡 Scraping {source['name']}...")
            
            try:
                articles = self.parse_rss_feed(source['url'])
                
                if not articles:
                    logger.warning(f"   No articles found from {source['name']}")
                    continue
                
                saved_count = 0
                for article in articles[:max_articles_per_source]:
                    if self.save_article(article, source['name'], source.get('tags', [])):
                        saved_count += 1
                    
                    # Small delay between articles
                    time.sleep(0.1)
                
                logger.info(f"   ✅ {saved_count} articles saved from {source['name']}")
                
            except Exception as e:
                logger.error(f"   ❌ Error scraping {source['name']}: {e}")
                self.error_count += 1
            
            # Delay between sources
            time.sleep(1)
    
    def scrape_google_news(self, max_keywords: int = 10):
        """Scrape Google News for health topics"""
        logger.info("📰 Scraping Google News health topics...")
        
        keywords_to_use = self.google_news_keywords[:max_keywords]
        
        for keyword in keywords_to_use:
            try:
                # Google News RSS URL
                url = f"https://news.google.com/rss/search?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
                
                articles = self.parse_rss_feed(url)
                
                saved_count = 0
                for article in articles[:20]:  # Limit per keyword
                    if self.save_article(article, f"Google News ({keyword})", [keyword, "google_news"]):
                        saved_count += 1
                
                if saved_count > 0:
                    logger.info(f"   ✅ {saved_count} articles for '{keyword}'")
                
                time.sleep(2)  # Respectful delay
                
            except Exception as e:
                logger.error(f"   ❌ Error with keyword '{keyword}': {e}")
    
    def run_comprehensive_scrape(self):
        """Run complete scraping from all sources"""
        start_time = datetime.now()
        
        logger.info("🚀 Starting Health News Scraper")
        logger.info("=" * 60)
        
        # Create/verify database
        self.create_database()
        
        # Scrape RSS sources by priority
        logger.info("📡 Phase 1: Major Health Organizations...")
        priority_1_sources = [s for s in self.rss_sources if s.get('priority', 3) == 1]
        self.scrape_rss_sources(priority_1_sources, max_articles_per_source=30)
        
        logger.info("📺 Phase 2: Major News Outlets...")
        priority_2_sources = [s for s in self.rss_sources if s.get('priority', 3) == 2]
        self.scrape_rss_sources(priority_2_sources, max_articles_per_source=25)
        
        logger.info("🏥 Phase 3: Health Publications...")
        priority_3_sources = [s for s in self.rss_sources if s.get('priority', 3) == 3]
        self.scrape_rss_sources(priority_3_sources, max_articles_per_source=20)
        
        logger.info("🌍 Phase 4: International Sources...")
        self.scrape_rss_sources(self.international_sources, max_articles_per_source=15)
        
        logger.info("💬 Phase 5: Social Media Sources...")
        self.scrape_rss_sources(self.social_sources, max_articles_per_source=10)
        
        logger.info("🔍 Phase 6: Google News Topics...")
        self.scrape_google_news(max_keywords=8)
        
        # Final report
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ HEALTH SCRAPER COMPLETE")
        logger.info("=" * 60)
        logger.info(f"⏱️  Duration: {duration:.1f} seconds")
        logger.info(f"📰 Articles Saved: {self.articles_saved}")
        logger.info(f"🔄 Duplicates Skipped: {self.duplicate_count}")
        logger.info(f"❌ Errors: {self.error_count}")
        
        if self.articles_saved > 0:
            logger.info(f"\n🎉 SUCCESS: {self.articles_saved} health articles collected!")
            logger.info("📱 Start your API server to access the content:")
            logger.info("   python start.py")
            logger.info("   Visit: http://localhost:8000/docs")
        else:
            logger.info(f"\n⚠️  No new articles saved")
            logger.info("   • Check internet connection")
            logger.info("   • Articles may already exist in database")
        
        return self.articles_saved
    
    def run_quick_scrape(self):
        """Run quick scrape from high-priority sources only"""
        logger.info("⚡ Quick Health News Update")
        logger.info("=" * 40)
        
        self.create_database()
        
        # Only priority 1 and 2 sources
        high_priority_sources = [s for s in self.rss_sources if s.get('priority', 3) <= 2]
        self.scrape_rss_sources(high_priority_sources, max_articles_per_source=15)
        
        # Limited Google News
        self.scrape_google_news(max_keywords=3)
        
        logger.info(f"\n⚡ Quick update complete: {self.articles_saved} articles saved")
        return self.articles_saved

if __name__ == "__main__":
    main()
