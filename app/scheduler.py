#!/usr/bin/env python3
"""
Background Scheduler for METABOLIC_BACKEND
Handles automatic scraping tasks using APScheduler - Cloud Optimized for Render
"""

import logging
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import sys

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthNewsScheduler:
    """Background scheduler for health news scraping tasks - Cloud Optimized"""
    
    def __init__(self):
        # Configure scheduler for cloud environment with thread pool
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=2)  # Limit concurrent jobs
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace time for missed executions
        }
        
        self.scheduler = BlockingScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'  # Use UTC for cloud deployment
        )
        self.is_running = False
        
        # Cloud environment detection
        self.is_cloud = os.getenv('RENDER') is not None or os.getenv('RAILWAY_ENVIRONMENT') is not None
        
    def scrape_health_news(self):
        """Background task to scrape health news - Thread-safe"""
        try:
            logger.info("🕷️ Starting scheduled health news scraping...")
            
            # Try the main scraper first
            try:
                from app.scrapers.master_health_scraper import MasterHealthScraper
                scraper = MasterHealthScraper()
                result = scraper.run_scraping()
                
                logger.info(f"✅ Scheduled scraping completed: {result['total_saved']} articles saved")
                
                # Log additional metrics for cloud monitoring
                if self.is_cloud:
                    logger.info(f"📊 Cloud Metrics - Sources: {result['sources_processed']}, Scraped: {result['total_scraped']}, Saved: {result['total_saved']}")
                
                return result
                
            except ImportError as e:
                if "cgi" in str(e):
                    logger.warning("⚠️ Python 3.13 compatibility issue detected, using master scraper in fallback mode")
                    
                    # Use the master scraper in fallback mode
                    from app.scrapers.master_health_scraper import MasterHealthScraper
                    scraper = MasterHealthScraper()
                    result = scraper.run_scraping()
                    logger.info(f"✅ Fallback scraping completed: {result.get('total_saved', 0)} articles saved")
                    return result
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"❌ Scheduled scraping failed: {e}")
            # Don't raise in cloud environment to prevent scheduler from stopping
            if not self.is_cloud:
                raise
            return {"error": str(e), "total_saved": 0}

    def cleanup_database(self):
        """Clean old articles and optimize database - Thread-safe"""
        try:
            logger.info("🧹 Starting database cleanup...")
            
            import sqlite3
            db_path = BASE_DIR / "data" / "articles.db"
            
            with sqlite3.connect(db_path, timeout=30.0, check_same_thread=False) as conn:
                # Delete articles older than 6 months
                six_months_ago = (datetime.now() - timedelta(days=180)).isoformat()
                
                cursor = conn.cursor()
                cursor.execute("DELETE FROM articles WHERE created_at < ?", (six_months_ago,))
                deleted_count = cursor.rowcount
                
                # Vacuum database to reclaim space
                conn.execute("VACUUM")
                
                logger.info(f"✅ Database cleanup completed: {deleted_count} old articles removed")
                
                if self.is_cloud:
                    logger.info(f"📊 Cloud DB Cleanup - Removed: {deleted_count} articles older than 6 months")
                    
        except Exception as e:
            logger.error(f"❌ Database cleanup failed: {e}")
            if not self.is_cloud:
                raise

    def keepalive_task(self):
        """Keepalive task to prevent cloud service from sleeping - Thread-safe"""
        try:
            logger.info("💓 Keepalive heartbeat - Scheduler active")
            
            # Simple database query to keep connection alive
            import sqlite3
            db_path = BASE_DIR / "data" / "articles.db"
            
            with sqlite3.connect(db_path, timeout=30.0, check_same_thread=False) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM articles")
                count = cursor.fetchone()[0]
                logger.info(f"💓 Database alive - {count} articles in database")
                
        except Exception as e:
            logger.error(f"❌ Keepalive task failed: {e}")

    def start_scheduler(self):
        """Start the background scheduler - Cloud Optimized"""
        try:
            if self.is_running:
                logger.warning("⚠️ Scheduler already running")
                return
                
            logger.info("🚀 Starting background scheduler...")
            
            # Cloud-optimized scheduling intervals
            if self.is_cloud:
                # More frequent scraping for cloud deployment (every 4 hours)
                scrape_interval = 4
                logger.info("☁️ Cloud environment detected - Using optimized intervals")
            else:
                # Less frequent for local development (every 6 hours)
                scrape_interval = 6
                logger.info("💻 Local environment detected - Using standard intervals")
            
            # Schedule health news scraping
            self.scheduler.add_job(
                self.scrape_health_news,
                trigger=IntervalTrigger(hours=scrape_interval),
                id='health_scraper',
                name='Health News Scraper',
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # Schedule database cleanup daily at 2 AM UTC
            self.scheduler.add_job(
                self.cleanup_database,
                trigger=CronTrigger(hour=2, minute=0, timezone='UTC'),
                id='database_cleanup',
                name='Database Cleanup',
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # Schedule immediate startup scraping (after 2 minutes to allow app to fully start)
            startup_time = datetime.now() + timedelta(minutes=2)
            self.scheduler.add_job(
                self.scrape_health_news,
                trigger=DateTrigger(run_date=startup_time),
                id='startup_scraper',
                name='Startup Health News Scraper',
                replace_existing=True
            )
            
            # Add keepalive job for cloud environments (every hour)
            if self.is_cloud:
                self.scheduler.add_job(
                    self.keepalive_task,
                    trigger=IntervalTrigger(hours=1),
                    id='keepalive',
                    name='Cloud Keepalive Task',
                    replace_existing=True,
                    max_instances=1
                )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("🚀 Background scheduler started successfully")
            logger.info(f"📅 Health news scraping: Every {scrape_interval} hours")
            logger.info("🧹 Database cleanup: Daily at 2:00 AM UTC")
            logger.info("⚡ Immediate scraping: Starting in 2 minutes")
            
            if self.is_cloud:
                logger.info("☁️ Cloud keepalive: Every hour")
                logger.info("🌐 Scheduler optimized for cloud deployment")
                
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}")
            raise
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Background scheduler stopped")
    
    def get_scheduled_jobs(self):
        """Get information about scheduled jobs"""
        jobs = []
        if self.scheduler:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
        return jobs
    
    def run_scraper_now(self):
        """Manually trigger scraper immediately - Thread-safe"""
        logger.info("🚀 Manual scraper trigger requested")
        return self.scrape_health_news()

# Global scheduler instance
health_scheduler = HealthNewsScheduler()
