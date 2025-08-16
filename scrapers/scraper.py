#!/usr/bin/env python3
"""
Health News Scraper

A comprehensive scraper that combines all functionality:
- RSS feeds from major health organizations (WHO, NIH, CDC)
- News outlets (Reuters, CNN, BBC, WebMD, Healthline)
- Google News health topics
- International health sources
- Social media health content (Reddit, YouTube)
- Indian health news sources

This replaces all individual scrapers with one unified solution.
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
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, quote_plus
from xml.etree import ElementTree as ET
import hashlib
import random

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Import URL validator
try:
    from app.url_validator import URLValidator
    URL_VALIDATOR_AVAILABLE = True
except ImportError:
    URL_VALIDATOR_AVAILABLE = False
    class URLValidator:
        def validate_article_url(self, article):
            return True, {"status": "valid"}

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = BASE_DIR / "data" / "articles.db"
if not DB_PATH.exists():
    DB_PATH = BASE_DIR / "db" / "articles.db"

class HealthScraper:
    """Comprehensive health news scraper"""
    
    def __init__(self):
        self.url_validator = URLValidator() if URL_VALIDATOR_AVAILABLE else None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        # Comprehensive RSS feed sources
        self.rss_sources = [
            # Major Health Organizations
            {
                "name": "WHO Health News",
                "url": "https://www.who.int/rss-feeds/news-english.xml",
                "category": "news",
                "tags": ["who", "international", "policy"],
                "priority": 1
            },
            {
                "name": "NIH News Releases", 
                "url": "https://www.nih.gov/news-events/news-releases/rss.xml",
                "category": "news",
                "tags": ["nih", "research", "government"],
                "priority": 1
            },
            {
                "name": "CDC Health News",
                "url": "https://tools.cdc.gov/api/v2/resources/media/403372.rss",
                "category": "news", 
                "tags": ["cdc", "prevention", "government"],
                "priority": 1
            },
            
            # Major News Outlets
            {
                "name": "Reuters Health",
                "url": "https://feeds.reuters.com/reuters/healthNews",
                "category": "news",
                "tags": ["reuters", "breaking"],
                "priority": 2
            },
            {
                "name": "CNN Health",
                "url": "http://rss.cnn.com/rss/edition_health.rss", 
                "category": "news",
                "tags": ["cnn", "breaking"],
                "priority": 2
            },
            {
                "name": "BBC Health",
                "url": "http://feeds.bbci.co.uk/news/health/rss.xml",
                "category": "news",
                "tags": ["bbc", "international"],
                "priority": 2
            },
            
            # Health-Specific Publications
            {
                "name": "WebMD Health News",
                "url": "https://www.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC",
                "category": "solutions",
                "tags": ["webmd", "consumer", "advice"],
                "priority": 3
            },
            {
                "name": "Healthline News",
                "url": "https://www.healthline.com/health-news/rss",
                "category": "solutions", 
                "tags": ["healthline", "wellness", "lifestyle"],
                "priority": 3
            },
            {
                "name": "Medical News Today",
                "url": "https://www.medicalnewstoday.com/rss",
                "category": "news",
                "tags": ["medical", "research"],
                "priority": 3
            }
        ]
        
        # Google News health keywords for comprehensive coverage
        self.google_news_keywords = [
            "health", "medical", "wellness", "nutrition", "fitness", "disease", 
            "vaccine", "therapy", "treatment", "prevention", "mental health",
            "diabetes", "cancer", "heart disease", "obesity", "covid",
            "healthcare", "public health", "medicine", "research"
        ]
        
        # Social media and alternative sources
        self.social_sources = [
            {
                "name": "Reddit Health",
                "url": "https://www.reddit.com/r/Health/.rss",
                "category": "blogs_and_opinions",
                "tags": ["reddit", "community", "discussion"]
            },
            {
                "name": "Reddit Medical",
                "url": "https://www.reddit.com/r/medicine/.rss", 
                "category": "blogs_and_opinions",
                "tags": ["reddit", "medical", "professionals"]
            }
        ]
        
        # International sources
        self.international_sources = [
            {
                "name": "Times of India Health",
                "url": "https://timesofindia.indiatimes.com/rssfeeds/3908999.cms",
                "category": "news",
                "tags": ["india", "international"],
                "priority": 4
            },
            {
                "name": "The Hindu Health",
                "url": "https://www.thehindu.com/sci-tech/health/feeder/default.rss",
                "category": "news", 
                "tags": ["india", "international"],
                "priority": 4
            }
        ]
        
        self.articles_saved = 0
        self.duplicate_count = 0
        self.error_count = 0
        
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
                        parsed_date = self._parse_date(pub_date)
                        
                        # Clean description
                        if description:
                            description = self._clean_html(description)
                            description = description[:500] + '...' if len(description) > 500 else description
                        
                        articles.append({
                            'title': title.strip()[:200],
                            'url': link.strip(),
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
            elem = element.find(tag_name) or element.find(f'.//{tag_name}')
            if elem is not None and elem.text:
                return elem.text.strip()
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
    
    def categorize_article(self, article: Dict) -> Tuple[str, List[str]]:
        """Smart categorization based on title and content"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        content = title + ' ' + summary
        
        # Category mapping
        if any(word in content for word in ['diabetes', 'blood sugar', 'insulin', 'glucose']):
            return 'diseases', ['diabetes', 'metabolic']
        elif any(word in content for word in ['cancer', 'tumor', 'oncology', 'chemotherapy']):
            return 'diseases', ['cancer', 'treatment']
        elif any(word in content for word in ['heart', 'cardiac', 'cardiovascular', 'cholesterol']):
            return 'diseases', ['cardiovascular', 'heart']
        elif any(word in content for word in ['mental health', 'depression', 'anxiety', 'stress']):
            return 'diseases', ['mental_health', 'wellness']
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
        """Save article to database with validation"""
        try:
            # URL validation
            if self.url_validator:
                is_valid, info = self.url_validator.validate_article_url(article)
                if not is_valid:
                    logger.debug(f"Invalid URL rejected: {article.get('url')} - {info.get('error')}")
                    return False
            
            # Categorize article
            category, auto_tags = self.categorize_article(article)
            all_tags = list(set(source_tags + auto_tags))
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO articles 
                (title, summary, url, source, date, categories, tags, author)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['title'],
                article.get('summary'),
                article['url'],
                source_name,
                article['date'],
                category,
                json.dumps(all_tags),
                article.get('author')
            ))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.debug(f"Saved: {article['title'][:60]}...")
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

def main():
    """Main function with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Health News Scraper")
    parser.add_argument("--quick", action="store_true", help="Run quick update (high-priority sources only)")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive scrape (all sources)")
    
    args = parser.parse_args()
    
    scraper = HealthScraper()
    
    if args.quick:
        articles_saved = scraper.run_quick_scrape()
    else:
        articles_saved = scraper.run_comprehensive_scrape()
    
    return articles_saved

if __name__ == "__main__":
    main()
