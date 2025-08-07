#!/usr/bin/env python3
"""
Database seeding script for Metabolical Backend
Creates initial database structure and adds sample articles if database is empty.
"""

import sys
import os
from pathlib import Path
import sqlite3
import json
from datetime import datetime

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

try:
    from app.utils import DB_PATH, initialize_optimizations, connection_pool
    print(f"✅ Successfully imported utils. Database path: {DB_PATH}")
except ImportError as e:
    print(f"❌ Failed to import utils: {e}")
    # Fallback database path
    DB_PATH = str(Path(__file__).parent / "data" / "articles.db")
    print(f"🔄 Using fallback database path: {DB_PATH}")

def create_sample_articles():
    """Create sample articles for testing"""
    sample_articles = [
        {
            "title": "Understanding Diabetes: Types, Symptoms, and Management",
            "summary": "A comprehensive guide to diabetes, covering Type 1, Type 2, and gestational diabetes, along with management strategies and lifestyle changes.",
            "url": "https://example-health.com/diabetes-guide",
            "source": "Health Information Network",
            "date": datetime.now().isoformat(),
            "categories": json.dumps(["diseases"]),
            "tags": json.dumps(["diabetes", "blood sugar", "health management"]),
            "authors": "Medical Team"
        },
        {
            "title": "Heart-Healthy Diet: Foods That Protect Your Cardiovascular System",
            "summary": "Discover the best foods for heart health, including omega-3 rich fish, leafy greens, and whole grains that support cardiovascular wellness.",
            "url": "https://example-health.com/heart-healthy-diet",
            "source": "Nutrition Today",
            "date": datetime.now().isoformat(),
            "categories": json.dumps(["nutrition", "solutions"]),
            "tags": json.dumps(["heart health", "nutrition", "cardiovascular", "diet"]),
            "authors": "Nutrition Experts"
        },
        {
            "title": "Mental Health Awareness: Breaking the Stigma",
            "summary": "Latest insights on mental health, addressing stigma, and promoting awareness about depression, anxiety, and available treatment options.",
            "url": "https://example-health.com/mental-health-awareness",
            "source": "Mental Health Foundation",
            "date": datetime.now().isoformat(),
            "categories": json.dumps(["news"]),
            "tags": json.dumps(["mental health", "awareness", "depression", "anxiety"]),
            "authors": "Psychology Team"
        },
        {
            "title": "The Power of Exercise: Physical Activity for All Ages",
            "summary": "How regular physical activity benefits people of all ages, from children to seniors, including recommended exercises and safety tips.",
            "url": "https://example-health.com/exercise-benefits",
            "source": "Fitness & Health Journal",
            "date": datetime.now().isoformat(),
            "categories": json.dumps(["solutions", "fitness"]),
            "tags": json.dumps(["exercise", "fitness", "physical activity", "wellness"]),
            "authors": "Fitness Specialists"
        },
        {
            "title": "Women's Health: Preventive Care and Wellness",
            "summary": "Essential preventive care for women, including regular screenings, reproductive health, and wellness tips for every stage of life.",
            "url": "https://example-health.com/womens-health",
            "source": "Women's Health Network",
            "date": datetime.now().isoformat(),
            "categories": json.dumps(["audience"]),
            "tags": json.dumps(["women", "preventive care", "wellness", "health screening"]),
            "authors": "Women's Health Team"
        }
    ]
    
    return sample_articles

def seed_database():
    """Initialize database and add sample data if empty"""
    try:
        # Ensure database directory exists
        db_dir = Path(DB_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Database directory: {db_dir}")
        
        # Initialize database
        print("🔧 Initializing database...")
        initialize_optimizations()
        
        # Check if database has articles
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            article_count = cursor.fetchone()[0]
            print(f"📊 Current article count: {article_count}")
            
            if article_count == 0:
                print("📝 Database is empty, adding sample articles...")
                sample_articles = create_sample_articles()
                
                for article in sample_articles:
                    cursor.execute("""
                        INSERT INTO articles (title, summary, url, source, date, categories, tags, authors)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        article["title"],
                        article["summary"],
                        article["url"],
                        article["source"],
                        article["date"],
                        article["categories"],
                        article["tags"],
                        article["authors"]
                    ))
                
                conn.commit()
                print(f"✅ Added {len(sample_articles)} sample articles to database")
            else:
                print("✅ Database already contains articles, skipping sample data")
        
        print("🎉 Database seeding completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        return False

if __name__ == "__main__":
    print("🌱 Starting database seeding...")
    success = seed_database()
    if success:
        print("✅ Database seeding completed successfully")
        sys.exit(0)
    else:
        print("❌ Database seeding failed")
        sys.exit(1)
