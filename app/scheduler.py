#!/usr/bin/env python3
"""
Background Scheduler for Metabolical Backend
Handles automated scraping and data updates with async/multithreading support
"""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import threading
import time
import concurrent.futures
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SourceConfig:
    """Configuration for a scraping source"""
    name: str
    url: str
    category: str
    tags: List[str]
    priority: int = 3
    timeout: int = 60

class BackgroundScheduler:
    """Background scheduler for running scrapers periodically with async support"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.scrapers_dir = self.base_dir / "scrapers"
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_full_scrape = None
        self.last_quick_scrape = None
        self.active_jobs = {}  # Track running jobs
        self.max_concurrent_sources = 5  # Limit concurrent scraping
        
    def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Background scheduler started with async support")
        
    def stop(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Background scheduler stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop with improved timing"""
        logger.info("📅 Scheduler loop started")
        
        # Run initial quick scrape on startup
        self._run_quick_scrape_async()
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Check if we need to run a full scrape (every 12 hours)
                if (self.last_full_scrape is None or 
                    current_time - self.last_full_scrape > timedelta(hours=12)):
                    self._run_full_scrape_async()
                    self.last_full_scrape = current_time
                
                # Check if we need to run a quick scrape (every 15 minutes for more frequent updates)
                elif (self.last_quick_scrape is None or 
                      current_time - self.last_quick_scrape > timedelta(minutes=15)):
                    self._run_quick_scrape_async()
                    self.last_quick_scrape = current_time
                
                # Sleep for 5 minutes before checking again (more responsive)
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(300)  # Sleep 5 minutes on error
                
    def _run_full_scrape_async(self):
        """Run comprehensive scraping with async support"""
        job_id = f"full_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info("🚀 Starting full scrape with parallel processing...")
            
            # Use thread pool for parallel execution
            thread = threading.Thread(
                target=self._execute_scrape_with_parallelism,
                args=("comprehensive", job_id),
                daemon=True
            )
            thread.start()
            
            self.active_jobs[job_id] = {
                'type': 'full',
                'started': datetime.now(),
                'thread': thread
            }
            
        except Exception as e:
            logger.error(f"❌ Error starting full scrape: {e}")
            
    def _run_quick_scrape_async(self):
        """Run quick scraping with async support"""
        job_id = f"quick_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info("⚡ Starting quick scrape with parallel processing...")
            
            # Use thread pool for parallel execution
            thread = threading.Thread(
                target=self._execute_scrape_with_parallelism,
                args=("quick", job_id),
                daemon=True
            )
            thread.start()
            
            self.active_jobs[job_id] = {
                'type': 'quick',
                'started': datetime.now(),
                'thread': thread
            }
            
        except Exception as e:
            logger.error(f"❌ Error starting quick scrape: {e}")
    
    def _execute_scrape_with_parallelism(self, scrape_type: str, job_id: str):
        """Execute scraping with parallel processing of sources"""
        try:
            start_time = datetime.now()
            
            # Import the scraper here to avoid circular imports
            try:
                sys.path.append(str(self.scrapers_dir))
                from scraper import EnhancedHealthScraper
            except ImportError as e:
                logger.error(f"Could not import scraper: {e}")
                return
            
            # Create scraper instance
            scraper = EnhancedHealthScraper()
            scraper.create_database()
            
            # Get source configuration based on scrape type
            if scrape_type == "comprehensive":
                sources = self._get_comprehensive_sources(scraper)
                max_articles_per_source = 30
            else:  # quick
                sources = self._get_quick_sources(scraper)
                max_articles_per_source = 15
            
            # Execute scraping with parallel processing
            total_saved = self._scrape_sources_parallel(scraper, sources, max_articles_per_source)
            
            # Clean up duplicates if it's a comprehensive scrape
            if scrape_type == "comprehensive":
                duplicates_removed = scraper.cleanup_duplicates()
                logger.info(f"🧹 Cleaned up {duplicates_removed} duplicate articles")
            
            # Final report
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ {scrape_type.title()} scrape completed in {duration:.1f}s")
            logger.info(f"📰 Articles saved: {total_saved}, Duplicates: {scraper.duplicate_count}, Errors: {scraper.error_count}")
            
        except Exception as e:
            logger.error(f"❌ Error in parallel scrape execution: {e}")
        finally:
            # Clean up job tracking
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def _get_comprehensive_sources(self, scraper) -> List[Dict]:
        """Get all sources for comprehensive scraping"""
        return scraper.rss_sources
    
    def _get_quick_sources(self, scraper) -> List[Dict]:
        """Get high-priority sources for quick scraping"""
        return [s for s in scraper.rss_sources if s.get('priority', 3) <= 2]
    
    def _scrape_sources_parallel(self, scraper, sources: List[Dict], max_articles: int) -> int:
        """Scrape sources in parallel using ThreadPoolExecutor"""
        total_saved = 0
        
        try:
            # Group sources by priority for better load distribution
            priority_groups = {}
            for source in sources:
                priority = source.get('priority', 3)
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append(source)
            
            # Process each priority group
            for priority in sorted(priority_groups.keys()):
                priority_sources = priority_groups[priority]
                logger.info(f"🔄 Processing priority {priority} sources: {len(priority_sources)} sources")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_sources) as executor:
                    # Submit all sources in this priority group
                    future_to_source = {
                        executor.submit(self._scrape_single_source, scraper, source, max_articles): source
                        for source in priority_sources
                    }
                    
                    # Collect results as they complete
                    for future in concurrent.futures.as_completed(future_to_source, timeout=300):
                        source = future_to_source[future]
                        try:
                            saved_count = future.result()
                            total_saved += saved_count
                            logger.info(f"   ✅ {source['name']}: {saved_count} articles")
                        except Exception as e:
                            logger.error(f"   ❌ {source['name']}: {e}")
                
                # Brief pause between priority groups
                if priority < max(priority_groups.keys()):
                    time.sleep(2)
            
            # Process Google News separately with limited keywords
            google_saved = self._scrape_google_news_parallel(scraper)
            total_saved += google_saved
            
        except Exception as e:
            logger.error(f"Error in parallel scraping: {e}")
        
        return total_saved
    
    def _scrape_single_source(self, scraper, source: Dict, max_articles: int) -> int:
        """Scrape a single source (for use in thread pool)"""
        try:
            articles = scraper.parse_rss_feed(source['url'])
            
            if not articles:
                return 0
            
            saved_count = 0
            for article in articles[:max_articles]:
                if scraper.save_article(article, source['name'], source.get('tags', [])):
                    saved_count += 1
                
                # Small delay between articles to be respectful
                time.sleep(0.1)
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")
            return 0
    
    def _scrape_google_news_parallel(self, scraper) -> int:
        """Scrape Google News with limited keywords for faster execution"""
        try:
            # Use only top keywords for quick scraping
            quick_keywords = [
                "health", "medical", "nutrition", "diabetes", "heart disease",
                "mental health", "covid", "vaccine", "cancer", "obesity"
            ]
            
            total_saved = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit keyword searches
                future_to_keyword = {
                    executor.submit(self._scrape_google_keyword, scraper, keyword): keyword
                    for keyword in quick_keywords
                }
                
                # Collect results
                for future in concurrent.futures.as_completed(future_to_keyword, timeout=120):
                    keyword = future_to_keyword[future]
                    try:
                        saved_count = future.result()
                        total_saved += saved_count
                        if saved_count > 0:
                            logger.info(f"   📰 Google News '{keyword}': {saved_count} articles")
                    except Exception as e:
                        logger.error(f"   ❌ Google News '{keyword}': {e}")
            
            return total_saved
            
        except Exception as e:
            logger.error(f"Error in Google News scraping: {e}")
            return 0
    
    def _scrape_google_keyword(self, scraper, keyword: str) -> int:
        """Scrape Google News for a single keyword"""
        try:
            from urllib.parse import quote_plus
            url = f"https://news.google.com/rss/search?q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
            
            articles = scraper.parse_rss_feed(url)
            
            saved_count = 0
            for article in articles[:10]:  # Limit per keyword
                if scraper.save_article(article, f"Google News ({keyword})", [keyword, "google_news"]):
                    saved_count += 1
            
            time.sleep(1)  # Respectful delay
            return saved_count
            
        except Exception as e:
            logger.error(f"Error scraping Google News keyword '{keyword}': {e}")
            return 0
    
    def get_status(self):
        """Get enhanced scheduler status"""
        active_job_info = {}
        for job_id, job_info in self.active_jobs.items():
            active_job_info[job_id] = {
                'type': job_info['type'],
                'started': job_info['started'].isoformat(),
                'duration_seconds': (datetime.now() - job_info['started']).total_seconds(),
                'is_alive': job_info['thread'].is_alive()
            }
        
        return {
            "is_running": self.is_running,
            "last_full_scrape": self.last_full_scrape.isoformat() if self.last_full_scrape else None,
            "last_quick_scrape": self.last_quick_scrape.isoformat() if self.last_quick_scrape else None,
            "next_full_scrape": (self.last_full_scrape + timedelta(hours=12)).isoformat() if self.last_full_scrape else "Soon",
            "next_quick_scrape": (self.last_quick_scrape + timedelta(minutes=15)).isoformat() if self.last_quick_scrape else "Soon",
            "active_jobs": active_job_info,
            "max_concurrent_sources": self.max_concurrent_sources
        }
        
    def trigger_manual_scrape(self, scrape_type="quick"):
        """Manually trigger a scrape with async support"""
        try:
            logger.info(f"🎯 Manual {scrape_type} scrape triggered")
            
            if scrape_type == "full" or scrape_type == "comprehensive":
                self._run_full_scrape_async()
                return "Full comprehensive scrape triggered with parallel processing"
            else:
                self._run_quick_scrape_async()
                return "Quick scrape triggered with parallel processing"
                
        except Exception as e:
            logger.error(f"Error triggering manual scrape: {e}")
            return f"Error: {str(e)}"

# Global scheduler instance
scheduler = BackgroundScheduler()