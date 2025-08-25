#!/usr/bin/env python3
"""
Database Article Cleaner
Fixes special characters and duplicate title/summary in existing articles
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.scraper import EnhancedHealthScraper

def main():
    print("🧹 Starting database article cleaning process...")
    
    try:
        # Initialize scraper
        scraper = EnhancedHealthScraper()
        
        # Clean existing articles
        fixed_count = scraper.clean_existing_articles_in_db()
        
        print(f"✅ Successfully cleaned {fixed_count} articles!")
        print("📊 Articles with special characters and duplicate summaries have been fixed.")
        
    except Exception as e:
        print(f"❌ Error during cleaning: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
