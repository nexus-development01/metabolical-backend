#!/usr/bin/env python3
"""
Remove Low-Quality Articles Script
Removes articles with weak, generic, or duplicate summaries
"""

import sqlite3
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def remove_low_quality_articles():
    """Remove articles with weak or generic summaries"""
    
    print("🧹 Starting removal of low-quality articles...")
    
    # Get database path
    db_path = Path(__file__).parent / 'data' / 'articles.db'
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Define patterns for weak/generic summaries to remove
        weak_summary_patterns = [
            "Medical research findings and scientific studies with implications for patient care and health outcomes",
            "Comprehensive, up-to-date news coverage, aggregated from sources all over the world by Google",
            "(study page | release notes)",
            "study page | release notes",
        ]
        
        # Find articles with these weak summaries
        total_removed = 0
        
        for pattern in weak_summary_patterns:
            cursor.execute('''
                SELECT id, title, summary FROM articles 
                WHERE summary LIKE ? OR summary = ?
            ''', (f'%{pattern}%', pattern))
            
            articles_to_remove = cursor.fetchall()
            
            if articles_to_remove:
                print(f"🗑️  Found {len(articles_to_remove)} articles with pattern: '{pattern[:50]}...'")
                
                # Delete these articles
                article_ids = [str(article[0]) for article in articles_to_remove]
                placeholders = ','.join(['?' for _ in article_ids])
                
                cursor.execute(f'''
                    DELETE FROM articles 
                    WHERE id IN ({placeholders})
                ''', article_ids)
                
                removed_count = cursor.rowcount
                total_removed += removed_count
                print(f"✅ Removed {removed_count} articles with weak summary pattern")
        
        # Also remove articles with very short or empty summaries
        cursor.execute('''
            DELETE FROM articles 
            WHERE summary IS NULL 
               OR LENGTH(TRIM(summary)) < 10
               OR summary = ''
        ''')
        
        short_summary_removed = cursor.rowcount
        total_removed += short_summary_removed
        
        if short_summary_removed > 0:
            print(f"✅ Removed {short_summary_removed} articles with very short/empty summaries")
        
        # Remove duplicate titles (keep the most recent)
        cursor.execute('''
            DELETE FROM articles 
            WHERE id NOT IN (
                SELECT MAX(id) 
                FROM articles 
                GROUP BY title
            )
        ''')
        
        duplicate_removed = cursor.rowcount
        total_removed += duplicate_removed
        
        if duplicate_removed > 0:
            print(f"✅ Removed {duplicate_removed} duplicate articles (kept most recent)")
        
        conn.commit()
        conn.close()
        
        print(f"🎉 Successfully removed {total_removed} low-quality articles!")
        print("📊 Database now contains only high-quality articles with meaningful summaries.")
        
    except Exception as e:
        print(f"❌ Error removing low-quality articles: {e}")
        raise

if __name__ == "__main__":
    remove_low_quality_articles()
