#!/usr/bin/env python3
"""
Simple runner script for METABOLIC_BACKEND
"""

import sys
import subprocess
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
    """Run database cleanup"""
    print("🧹 Cleaning database...")
    subprocess.run([sys.executable, "scripts/cleanup_urls.py"])

def check_urls():
    """Check URL status"""
    print("🔍 Checking URLs...")
    subprocess.run([sys.executable, "scripts/check_urls.py"])

def show_help():
    """Show available commands"""
    print("""
🏥 METABOLIC_BACKEND - Available Commands:

  api         Start the FastAPI server
  scraper     Run the health news scraper  
  clean       Clean up problematic URLs from database
  check       Check URL status in database
  help        Show this help message

Usage:
  python run.py <command>

Examples:
  python run.py api
  python run.py scraper
  python run.py clean
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
        check_urls()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        sys.exit(1)
