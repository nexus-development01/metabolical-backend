#!/usr/bin/env python3
"""
Simple Health News Scraper - Python 3.13 Compatible
A basic scraper that works without feedparser for Python 3.13 compatibility
"""

import sys
from pathlib import Path
import requests
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = BASE_DIR / "data" / "articles.db"

class SimpleHealthScraper:
    """Simple health news scraper compatible with Python 3.13"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
        # Simple RSS sources that work well with basic XML parsing
        self.rss_sources = [
            {
                "name": "BBC Health",
                "url": "http://feeds.bbci.co.uk/news/health/rss.xml",
                "category": "health_news"
            },
            {
                "name": "Reuters Health",
                "url": "https://feeds.reuters.com/reuters/health",
                "category": "health_news"
            },
            {
                "name": "WHO News",
                "url": "https://www.who.int/rss-feeds/news-english.xml",
                "category": "public_health"
            }
        ]
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    title TEXT,
                    authors TEXT,
                    summary TEXT,
                    url TEXT,
                    categories TEXT,
                    tags TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    priority INTEGER DEFAULT 1,
                    url_health TEXT,
                    url_accessible INTEGER DEFAULT 1,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subcategory TEXT,
                    news_score REAL DEFAULT 0.5,
                    trending_score REAL DEFAULT 0.5,
                    content_quality_score REAL DEFAULT 0.5
                )
            """)
            conn.commit()
    
    def parse_rss_with_xml(self, url: str, source_info: Dict) -> List[Dict]:
        """Parse RSS feed using basic XML parsing"""
        articles = []
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle different RSS formats
            items = root.findall('.//item')  # Standard RSS
            if not items:
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')  # Atom format
            
            for item in items[:10]:  # Limit to 10 articles per source
                try:
                    # Extract basic fields
                    title_elem = item.find('title') or item.find('.//{http://www.w3.org/2005/Atom}title')
                    link_elem = item.find('link') or item.find('.//{http://www.w3.org/2005/Atom}link')
                    desc_elem = item.find('description') or item.find('.//{http://www.w3.org/2005/Atom}summary')
                    date_elem = item.find('pubDate') or item.find('.//{http://www.w3.org/2005/Atom}published')
                    
                    if not title_elem or not link_elem:
                        continue
                    
                    title = self.clean_text(title_elem.text or "")
                    url = link_elem.text or link_elem.get('href', '')
                    description = self.clean_text(desc_elem.text or "") if desc_elem is not None else ""
                    pub_date = date_elem.text if date_elem is not None else datetime.now().isoformat()
                    
                    if title and url:
                        article = {
                            'title': title[:200],  # Limit title length
                            'summary': description[:500],  # Limit summary length
                            'url': url,
                            'date': self.parse_date(pub_date),
                            'source': source_info['name'],
                            'categories': json.dumps([source_info['category']]),
                            'tags': json.dumps(['health', 'news']),
                            'authors': '',
                            'subcategory': source_info['category'],
                            'priority': 1,
                            'url_accessible': 1,
                            'last_checked': datetime.now().isoformat()
                        }
                        
                        articles.append(article)
                        
                except Exception as e:
                    logger.warning(f"Error parsing item from {source_info['name']}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping {source_info['name']}: {e}")
        
        return articles
    
    def clean_text(self, text: str) -> str:
        """Clean HTML and normalize text"""
        if not text:
            return ""
        
        # Basic HTML tag removal
        try:
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text()
        except:
            # Fallback: simple regex
            import re
            text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace and entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        
        return text.strip()
    
    def parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format"""
        if not date_str:
            return datetime.now().isoformat()
        
        # Common date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %Z',
            '%a, %d %b %Y %H:%M:%S %z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat()
            except:
                continue
        
        return datetime.now().isoformat()
    
    def save_articles(self, articles: List[Dict]) -> int:
        """Save articles to database"""
        if not articles:
            return 0
        
        saved_count = 0
        
        with sqlite3.connect(DB_PATH) as conn:
            for article in articles:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO articles 
                        (date, title, authors, summary, url, categories, tags, source, 
                         priority, url_accessible, last_checked, subcategory, 
                         news_score, trending_score, content_quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        article['date'],
                        article['title'],
                        article['authors'],
                        article['summary'],
                        article['url'],
                        article['categories'],
                        article['tags'],
                        article['source'],
                        article['priority'],
                        article['url_accessible'],
                        article['last_checked'],
                        article['subcategory'],
                        0.7,  # news_score
                        0.5,  # trending_score
                        0.6   # content_quality_score
                    ))
                    
                    if conn.total_changes > 0:
                        saved_count += 1
                        logger.info(f"✅ Saved: {article['title'][:60]}...")
                        
                except Exception as e:
                    logger.error(f"Error saving article '{article['title'][:50]}...': {e}")
            
            conn.commit()
        
        return saved_count
    
    def run_scraping(self) -> Dict:
        """Run the complete scraping process"""
        logger.info("🚀 Starting Simple Health Scraper (Python 3.13 compatible)...")
        
        # Initialize database
        self.init_database()
        
        all_articles = []
        sources_processed = 0
        
        # Scrape RSS sources
        for source in self.rss_sources:
            logger.info(f"🔍 Scraping {source['name']}...")
            articles = self.parse_rss_with_xml(source['url'], source)
            all_articles.extend(articles)
            sources_processed += 1
            
            # Be respectful - small delay between requests
            import time
            time.sleep(2)
        
        # Save to database
        saved_count = self.save_articles(all_articles)
        
        result = {
            'total_scraped': len(all_articles),
            'total_saved': saved_count,
            'sources_processed': sources_processed,
            'timestamp': datetime.now().isoformat(),
            'scraper_type': 'simple_compatible'
        }
        
        logger.info(f"✅ Simple scraping completed: {saved_count}/{len(all_articles)} articles saved from {sources_processed} sources")
        return result

def main():
    """Main execution function"""
    scraper = SimpleHealthScraper()
    result = scraper.run_scraping()
    
    print("\n" + "="*60)
    print("🏥 SIMPLE HEALTH SCRAPER - RESULTS")
    print("="*60)
    print(f"📊 Total Articles Scraped: {result['total_scraped']}")
    print(f"💾 Articles Saved to Database: {result['total_saved']}")
    print(f"🌐 Sources Processed: {result['sources_processed']}")
    print(f"⏰ Completed at: {result['timestamp']}")
    print(f"🔧 Scraper Type: {result['scraper_type']}")
    print("="*60)
    
    return result

if __name__ == "__main__":
    main()
