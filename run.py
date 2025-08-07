#!/usr/bin/env python3
"""
Simple runner script for METABOLIC_BACKEND
"""

import sys
import subprocess
import asyncio
from pathlib import Path

def run_api():
    """Run the FastAPI server"""
    print("🚀 Starting METABOLIC_BACKEND API...")
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "app.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000",
        "--reload"
    ])

def run_scraper():
    """Run the health news scraper"""
    print("🕷️ Starting health news scraper...")
    subprocess.run([sys.executable, "app/scrapers/master_health_scraper.py"])

def clean_database():
    """Run database cleanup using scheduler's cleanup function"""
    print("🧹 Cleaning database...")
    try:
        # Import and run the cleanup function from the scheduler
        import asyncio
        from app.scheduler import HealthNewsScheduler
        
        async def run_cleanup():
            scheduler = HealthNewsScheduler()
            await scheduler.cleanup_database()
        
        asyncio.run(run_cleanup())
        print("✅ Database cleanup completed")
    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")

def check_database():
    """Check database status and article counts"""
    print("🔍 Checking database status...")
    try:
        from app.utils import get_total_articles_count
        import sqlite3
        from pathlib import Path
        
        # Get article count
        count = get_total_articles_count()
        print(f"📊 Total articles in database: {count}")
        
        # Check database file
        db_path = Path("data/articles.db")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"💾 Database file size: {size_mb:.2f} MB")
        else:
            print("⚠️ Database file not found")
            
        # Check recent articles
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM articles 
                WHERE date >= datetime('now', '-7 days')
            """)
            recent_count = cursor.fetchone()[0]
            print(f"📅 Articles from last 7 days: {recent_count}")
            
        print("✅ Database check completed")
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")

def show_help():
    """Show available commands"""
    print("""
🏥 METABOLIC_BACKEND - Available Commands:

  api         Start the FastAPI server
  scraper     Run the health news scraper  
  clean       Clean up old articles from database
  check       Check database status and article counts
  help        Show this help message

Usage:
  python run.py <command>

Examples:
  python run.py api
  python run.py scraper
  python run.py clean
  python run.py check
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "api":
        run_api()
    elif command == "scraper":
        run_scraper()
    elif command == "clean":
        clean_database()
    elif command == "check":
        check_database()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        sys.exit(1)
