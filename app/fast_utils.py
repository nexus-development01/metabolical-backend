"""
Ultra-fast utilities for maximum performance
"""

import sqlite3
import json
from typing import Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "articles.db"

def get_articles_ultra_fast(page: int = 1, limit: int = 20) -> Dict:
    """Ultra-fast article retrieval with minimal processing"""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-32000")  # 32MB cache
        conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        
        # Fast count
        cursor.execute("SELECT COUNT(1) FROM articles")
        total = cursor.fetchone()[0]
        
        # Fast pagination
        offset = (page - 1) * limit
        total_pages = (total + limit - 1) // limit
        
        # Ultra-simple query
        cursor.execute("""
            SELECT id, title, summary, url, source, date, categories as category, tags
            FROM articles 
            ORDER BY date DESC 
            LIMIT ? OFFSET ?
        """, [limit, offset])
        
        rows = cursor.fetchall()
        
        # Minimal processing
        articles = []
        for row in rows:
            article = {
                'id': row['id'],
                'title': row['title'] or 'Health Article',
                'summary': row['summary'] or 'Health news summary',
                'url': row['url'],
                'source': row['source'] or 'Health News',
                'date': row['date'],
                'category': row['category'],
                'tags': []
            }
            
            # Fast tag parsing
            if row['tags']:
                try:
                    if row['tags'].startswith('['):
                        article['tags'] = json.loads(row['tags'])
                    else:
                        article['tags'] = [t.strip() for t in row['tags'].split(',') if t.strip()]
                except:
                    article['tags'] = []
            
            articles.append(article)
        
        conn.close()
        
        return {
            "articles": articles,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
    except Exception as e:
        logger.error(f"Error in get_articles_ultra_fast: {e}")
        return {
            "articles": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False
        }

def search_articles_ultra_fast(query: str, page: int = 1, limit: int = 20) -> Dict:
    """Ultra-fast search with minimal processing"""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-32000")
        conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        
        # Simple search query
        search_condition = f"%{query}%"
        
        # Fast count
        cursor.execute("""
            SELECT COUNT(1) FROM articles 
            WHERE title LIKE ? OR summary LIKE ?
        """, [search_condition, search_condition])
        total = cursor.fetchone()[0]
        
        # Fast pagination
        offset = (page - 1) * limit
        total_pages = (total + limit - 1) // limit
        
        # Search query
        cursor.execute("""
            SELECT id, title, summary, url, source, date, categories as category, tags
            FROM articles 
            WHERE title LIKE ? OR summary LIKE ?
            ORDER BY date DESC 
            LIMIT ? OFFSET ?
        """, [search_condition, search_condition, limit, offset])
        
        rows = cursor.fetchall()
        
        # Minimal processing
        articles = []
        for row in rows:
            article = {
                'id': row['id'],
                'title': row['title'] or 'Health Article',
                'summary': row['summary'] or 'Health news summary',
                'url': row['url'],
                'source': row['source'] or 'Health News',
                'date': row['date'],
                'category': row['category'],
                'tags': []
            }
            
            # Fast tag parsing
            if row['tags']:
                try:
                    if row['tags'].startswith('['):
                        article['tags'] = json.loads(row['tags'])
                    else:
                        article['tags'] = [t.strip() for t in row['tags'].split(',') if t.strip()]
                except:
                    article['tags'] = []
            
            articles.append(article)
        
        conn.close()
        
        return {
            "articles": articles,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
    except Exception as e:
        logger.error(f"Error in search_articles_ultra_fast: {e}")
        return {
            "articles": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False
        }