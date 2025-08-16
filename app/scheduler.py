#!/usr/bin/env python3
"""
Background Scheduler for Metabolical Backend
Handles automated scraping and data updates
"""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundScheduler:
    """Background scheduler for running scrapers periodically"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.scrapers_dir = self.base_dir / "scrapers"
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_full_scrape = None
        self.last_quick_scrape = None
        
    def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Background scheduler started")
        
    def stop(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info(" Background scheduler stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info(" Scheduler loop started")
        
        # Run initial quick scrape on startup
        self._run_quick_scrape()
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Check if we need to run a full scrape (every 12 hours)
                if (self.last_full_scrape is None or 
                    current_time - self.last_full_scrape > timedelta(hours=12)):
                    self._run_full_scrape()
                    self.last_full_scrape = current_time
                
                # Check if we need to run a quick scrape (every 4 hours)
                elif (self.last_quick_scrape is None or 
                      current_time - self.last_quick_scrape > timedelta(hours=4)):
                    self._run_quick_scrape()
                    self.last_quick_scrape = current_time
                
                # Sleep for 30 minutes before checking again
                time.sleep(1800)  # 30 minutes
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(300)  # Sleep 5 minutes on error
                
    def _run_full_scrape(self):
        """Run comprehensive scraping"""
        try:
            logger.info("🚀 Starting full scrape...")
            
            scraper_path = self.scrapers_dir / "scraper.py"
            if not scraper_path.exists():
                logger.warning(f"Scraper not found: {scraper_path}")
                return
                
            # Run the scraper with comprehensive flag
            result = subprocess.run([
                sys.executable, str(scraper_path), "--comprehensive"
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            if result.returncode == 0:
                logger.info("✅ Full scrape completed successfully")
                logger.info(f"Output: {result.stdout[-200:]}")  # Last 200 chars
            else:
                logger.error(f"❌ Full scrape failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Full scrape timed out")
        except Exception as e:
            logger.error(f"❌ Error running full scrape: {e}")
            
    def _run_quick_scrape(self):
        """Run quick scraping (high priority sources only)"""
        try:
            logger.info("⚡ Starting quick scrape...")
            
            scraper_path = self.scrapers_dir / "scraper.py"
            if not scraper_path.exists():
                logger.warning(f"Scraper not found: {scraper_path}")
                return
                
            # Run the scraper with quick flag
            result = subprocess.run([
                sys.executable, str(scraper_path), "--quick"
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            if result.returncode == 0:
                logger.info("✅ Quick scrape completed successfully")
                logger.info(f"Output: {result.stdout[-200:]}")  # Last 200 chars
            else:
                logger.error(f"❌ Quick scrape failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Quick scrape timed out")
        except Exception as e:
            logger.error(f"❌ Error running quick scrape: {e}")
            
    def get_status(self):
        """Get scheduler status"""
        return {
            "is_running": self.is_running,
            "last_full_scrape": self.last_full_scrape.isoformat() if self.last_full_scrape else None,
            "last_quick_scrape": self.last_quick_scrape.isoformat() if self.last_quick_scrape else None,
            "next_full_scrape": (self.last_full_scrape + timedelta(hours=12)).isoformat() if self.last_full_scrape else "Soon",
            "next_quick_scrape": (self.last_quick_scrape + timedelta(hours=4)).isoformat() if self.last_quick_scrape else "Soon"
        }
        
    def trigger_manual_scrape(self, scrape_type="quick"):
        """Manually trigger a scrape"""
        try:
            logger.info(f"🎯 Manual {scrape_type} scrape triggered")
            
            if scrape_type == "full" or scrape_type == "comprehensive":
                threading.Thread(target=self._run_full_scrape, daemon=True).start()
                return "Full comprehensive scrape triggered"
            else:
                threading.Thread(target=self._run_quick_scrape, daemon=True).start()
                return "Quick scrape triggered"
                
        except Exception as e:
            logger.error(f"Error triggering manual scrape: {e}")
            return f"Error: {str(e)}"

# Global scheduler instance
scheduler = BackgroundScheduler()