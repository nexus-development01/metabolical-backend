"""
Metabolical Backend Utilities - Simplified and Clean
Database operations and utility functions for the health articles API.
"""

import sqlite3
import json
import threading
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from contextlib import contextmanager
import logging
import yaml
from pathlib import Path

# Import cache manager
try:
    from .cache_manager import cache_manager, db_cache, cached
except ImportError:
    # Fallback if cache manager is not available
    def cached(ttl=300, key_prefix=""):
        def decorator(func):
            return func
        return decorator
    
    class MockCache:
        def get_articles_cache_key(self, *args, **kwargs):
            return None
        def get_cached_articles(self, key):
            return None
        def cache_articles_result(self, key, result, ttl=180):
            pass
    
    db_cache = MockCache()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path - adjusted for new structure
DB_PATH = str(Path(__file__).parent.parent / "data" / "articles.db")

# Fallback to old path if new doesn't exist
if not Path(DB_PATH).exists():
    DB_PATH = str(Path(__file__).parent.parent / "db" / "articles.db")

# Category keywords file path - updated to use new unified config
CATEGORY_YAML_PATH = Path(__file__).parent / "health_categories.yml"

# Enhanced keyword mapping for better categorization
ENHANCED_KEYWORDS = {
    # NEWS CATEGORY
    "latest": [
        "breaking", "news", "recent", "update", "new study", "latest research",
        "announced", "report", "findings", "discovers", "reveals", "shows",
        "breakthrough", "development", "alert", "warning", "advisory"
    ],
    "policy and regulation": [
        "policy", "regulation", "law", "guideline", "standard", "rule",
        "government", "federal", "state", "ministry", "department",
        "FDA", "WHO", "CDC", "health department", "public health",
        "mandate", "requirement", "compliance", "approval"
    ],
    "govt schemes": [
        "scheme", "program", "initiative", "plan", "campaign",
        "government program", "health program", "public health initiative",
        "healthcare scheme", "medical scheme", "insurance", "coverage"
    ],
    "international": [
        "global", "international", "worldwide", "WHO", "world health",
        "pandemic", "epidemic", "outbreak", "country", "nation",
        "cross-border", "multinational", "universal"
    ],
    
    # DISEASES CATEGORY - Enhanced with symptoms and related terms
    "diabetes": [
        "diabetes", "diabetic", "blood sugar", "glucose", "insulin",
        "hyperglycemia", "hypoglycemia", "type 1", "type 2", "gestational",
        "prediabetes", "insulin resistance", "blood glucose", "diabetic complications",
        "glycemic", "metformin", "glucometer", "A1C", "hemoglobin"
    ],
    "obesity": [
        "obesity", "obese", "overweight", "weight loss", "weight gain",
        "BMI", "body mass index", "adipose", "fat", "bariatric",
        "metabolic syndrome", "weight management", "calorie", "portion"
    ],
    "inflammation": [
        "inflammation", "inflammatory", "inflamed", "swelling", "arthritis",
        "rheumatoid", "joint pain", "autoimmune", "immune system",
        "cytokine", "anti-inflammatory", "chronic inflammation"
    ],
    "cardiovascular": [
        "heart", "cardiac", "cardiovascular", "coronary", "artery",
        "blood pressure", "hypertension", "cholesterol", "stroke",
        "heart attack", "heart disease", "angina", "heart failure",
        "atherosclerosis", "cardiology", "ECG", "EKG"
    ],
    "liver": [
        "liver", "hepatic", "hepatitis", "cirrhosis", "fatty liver",
        "liver disease", "liver function", "bile", "jaundice",
        "liver enzymes", "hepatology"
    ],
    "kidney": [
        "kidney", "renal", "nephrology", "kidney disease", "dialysis",
        "kidney stones", "kidney failure", "creatinine", "urea",
        "nephritis", "chronic kidney disease"
    ],
    "thyroid": [
        "thyroid", "hypothyroid", "hyperthyroid", "thyroiditis",
        "goiter", "TSH", "T3", "T4", "thyroid hormone",
        "endocrine", "metabolism"
    ],
    "metabolic": [
        "metabolic", "metabolism", "metabolic syndrome", "endocrine",
        "hormone", "hormonal", "gland", "adrenal", "pituitary"
    ],
    "sleep disorders": [
        "sleep", "insomnia", "sleep apnea", "sleep disorder",
        "circadian", "melatonin", "sleep quality", "sleep patterns",
        "restless leg", "narcolepsy", "sleep study"
    ],
    "skin": [
        "skin", "dermatology", "dermatitis", "eczema", "psoriasis",
        "acne", "rash", "skin cancer", "melanoma", "dermatologist",
        "skincare", "complexion"
    ],
    "eyes and ears": [
        "eye", "vision", "ophthalmology", "glaucoma", "cataract",
        "macular degeneration", "ear", "hearing", "audiology",
        "tinnitus", "hearing loss", "ENT", "otolaryngology"
    ],
    "reproductive health": [
        "reproductive", "fertility", "pregnancy", "menstruation",
        "menopause", "contraception", "gynecology", "obstetrics",
        "sexual health", "hormone therapy", "PCOS", "endometriosis"
    ],
    
    # SOLUTIONS CATEGORY
    "nutrition": [
        "nutrition", "nutritional", "nutrient", "vitamin", "mineral",
        "diet", "dietary", "food", "eating", "meal", "supplement",
        "protein", "carbohydrate", "fat", "fiber", "antioxidant"
    ],
    "fitness": [
        "fitness", "exercise", "workout", "physical activity", "gym",
        "training", "cardio", "strength", "aerobic", "yoga",
        "pilates", "running", "walking", "swimming", "sports"
    ],
    "lifestyle": [
        "lifestyle", "healthy living", "wellness", "habit", "routine",
        "stress management", "work-life balance", "mindfulness",
        "self-care", "healthy choices", "behavior change"
    ],
    "wellness": [
        "wellness", "wellbeing", "holistic", "mind-body", "spiritual",
        "meditation", "relaxation", "balance", "harmony", "peace"
    ],
    "prevention": [
        "prevention", "preventive", "screening", "early detection",
        "vaccine", "immunization", "checkup", "prophylaxis",
        "risk reduction", "health maintenance"
    ],
    
    # FOOD CATEGORY - Enhanced
    "natural food": [
        "natural", "organic", "whole food", "unprocessed", "fresh",
        "raw", "clean eating", "farm-to-table", "locally sourced",
        "seasonal", "pesticide-free", "chemical-free"
    ],
    "organic food": [
        "organic", "organic food", "certified organic", "organic farming",
        "organic produce", "non-GMO", "sustainable", "eco-friendly",
        "biodynamic", "organic certification", "natural", "whole food"
    ],
    "processed food": [
        "processed", "packaged", "convenience food", "fast food",
        "junk food", "ultra-processed", "preservatives", "additives",
        "artificial", "refined", "instant", "frozen meal"
    ],
    "fish and seafood": [
        "fish", "seafood", "salmon", "tuna", "omega-3", "marine",
        "aquaculture", "fishing", "shellfish", "mercury", "sustainable fishing"
    ],
    "food safety": [
        "food safety", "foodborne", "contamination", "bacteria",
        "salmonella", "E. coli", "food poisoning", "hygiene",
        "food handling", "expiration", "storage", "recall"
    ],
    
    # AUDIENCE CATEGORY
    "women": [
        "women", "female", "woman", "maternal", "pregnancy",
        "menopause", "gynecology", "breast health", "women's health"
    ],
    "men": [
        "men", "male", "man", "prostate", "testosterone", "men's health",
        "masculine", "paternal", "andrology"
    ],
    "children": [
        "children", "child", "pediatric", "kids", "infant", "baby",
        "toddler", "childhood", "development", "growth", "vaccination"
    ],
    "teenagers": [
        "teenager", "teen", "adolescent", "youth", "puberty",
        "teenage", "young adult", "high school", "college"
    ],
    "seniors": [
        "senior", "elderly", "aging", "geriatric", "old age",
        "retirement", "age-related", "longevity", "mature adult"
    ],
    "athletes": [
        "athlete", "sports", "performance", "training", "competition",
        "endurance", "strength", "recovery", "sports medicine"
    ],
    "families": [
        "family", "household", "parent", "parenting", "family health",
        "home", "domestic", "caregiving", "family planning"
    ],
    
    # TRENDING CATEGORY
    "gut health": [
        "gut", "microbiome", "digestive", "intestinal", "probiotic",
        "prebiotic", "gut bacteria", "digestive health", "IBS",
        "gut-brain", "fermented", "fiber"
    ],
    "mental health": [
        "mental health", "depression", "anxiety", "stress", "psychology",
        "psychiatric", "mood", "emotional", "therapy", "counseling",
        "mindfulness", "cognitive", "behavioral"
    ],
    "hormones": [
        "hormone", "hormonal", "endocrine", "estrogen", "testosterone",
        "cortisol", "insulin", "thyroid hormone", "growth hormone",
        "hormone therapy", "hormone balance"
    ],
    "addiction": [
        "addiction", "substance abuse", "dependency", "withdrawal",
        "recovery", "rehabilitation", "alcohol", "drugs", "smoking",
        "nicotine", "opioid", "treatment"
    ],
    "sleep health": [
        "sleep", "sleep quality", "insomnia", "sleep disorder",
        "circadian rhythm", "melatonin", "sleep hygiene", "rest",
        "REM sleep", "sleep apnea"
    ],
    "sexual wellness": [
        "sexual", "sexuality", "intimacy", "libido", "sexual health",
        "reproductive", "contraception", "STD", "sexual dysfunction",
        "relationship", "intimate"
    ]
}

def get_enhanced_tag_conditions(tag: str) -> Tuple[str, List[str]]:
    """
    Enhanced tag matching using keywords, content analysis, and semantic matching
    Returns SQL WHERE condition and parameters for better categorization
    """
    
    # Get keywords for the requested tag
    keywords = ENHANCED_KEYWORDS.get(tag.lower(), [])
    
    # Basic tag matching (existing logic)
    tag_underscore = tag.replace(" ", "_")
    conditions = []
    params = []
    
    # 1. Enhanced tag matching for both JSON and comma-separated formats
    # JSON format: ["tag", "other"] and comma-separated: "tag, other, another"
    tag_underscore = tag.replace(" ", "_")
    tag_hyphen = tag.replace(" ", "-")
    
    # Match JSON format with quotes
    conditions.append('(LOWER(tags) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?))')
    params.extend([f'%"{tag}"%', f'%"{tag_underscore}"%'])
    
    # Match comma-separated format (with surrounding commas or at start/end)
    conditions.append('(LOWER(tags) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?))')
    params.extend([f'%{tag},%', f'%, {tag},%', f'%, {tag}', f'{tag},%'])
    
    # Also match hyphenated versions for tags like "covid-19"
    if "-" in tag or "_" in tag:
        conditions.append('(LOWER(tags) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?))')
        params.extend([f'%"{tag_hyphen}"%', f'%{tag_hyphen},%'])
    
    # 2. Enhanced keyword matching if available
    if keywords:
        # Keyword matching in tags
        keyword_conditions = []
        for keyword in keywords[:8]:  # Limit to top 8 keywords for performance
            keyword_conditions.append('LOWER(tags) LIKE LOWER(?)')
            params.append(f'%{keyword.lower()}%')
        
        if keyword_conditions:
            conditions.append(f'({" OR ".join(keyword_conditions)})')
        
        # Content-based matching (title and summary) for top keywords
        content_conditions = []
        for keyword in keywords[:4]:  # Top 4 keywords for content matching
            content_conditions.append('(LOWER(title) LIKE LOWER(?) OR LOWER(summary) LIKE LOWER(?))')
            params.extend([f'%{keyword.lower()}%', f'%{keyword.lower()}%'])
        
        if content_conditions:
            conditions.append(f'({" OR ".join(content_conditions)})')
    
    # Combine all conditions with OR logic
    final_condition = f'({" OR ".join(conditions)})'
    
    return final_condition, params

# Simple connection pool
class SQLiteConnectionPool:
    def __init__(self, database: str):
        self.database = database
        self._lock = threading.Lock()
        
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.database, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        try:
            yield conn
        finally:
            conn.close()

# Global connection pool
connection_pool = SQLiteConnectionPool(DB_PATH)

def is_valid_article_url(url: str) -> bool:
    """
    Check if an article URL is valid and accessible
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
    """
    if not url or url == '' or url == 'NULL':
        return False
    
    # Check for problematic URL patterns
    invalid_url_patterns = [
        'example.com', 'example.org', 'example.net',
        'domain.com', 'test.com', 'localhost',
        'javascript:', 'mailto:', 'file:', 'ftp:',
        '404', 'not-found', 'error',
        'google.com/rss/articles/',
        'dummy.com', 'sample.com'
    ]
    
    url_lower = url.lower()
    for pattern in invalid_url_patterns:
        if pattern in url_lower:
            return False
    
    # Check if URL has proper format
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Must be HTTP or HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False
            
    except Exception:
        return False
    
    return True

# Cache for category keywords
_category_cache = {}
_stats_cache = {}
_cache_timestamp = None

def get_cached_category_keywords() -> Dict:
    """Load and cache category keywords from YAML file"""
    global _category_cache
    
    if _category_cache:
        return _category_cache
        
    try:
        if CATEGORY_YAML_PATH.exists():
            with open(CATEGORY_YAML_PATH, 'r', encoding='utf-8') as file:
                _category_cache = yaml.safe_load(file) or {}
                logger.info(f"Loaded {len(_category_cache)} categories from {CATEGORY_YAML_PATH}")
        else:
            logger.warning(f"Category file not found: {CATEGORY_YAML_PATH}")
            _category_cache = {
                "diseases": {"diabetes": [], "obesity": [], "cardiovascular": []},
                "news": {"recent_developments": [], "policy_and_regulation": []},
                "solutions": {"medical_treatments": [], "preventive_care": []},
                "food": {"nutrition_basics": [], "superfoods": []},
                "audience": {"women": [], "men": [], "children": []},
                "blogs_and_opinions": {"expert_opinions": [], "patient_stories": []}
            }
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
        _category_cache = {}
        
    return _category_cache

def get_total_articles_count() -> int:
    """Get total number of articles in database"""
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error getting article count: {e}")
        return 0

def get_articles_paginated_optimized(
    page: int = 1,
    limit: int = 20,
    sort_by: str = "desc",
    search_query: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    tag: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """
    Optimized paginated article retrieval with search and filtering - Now with caching
    """
    # Generate cache key for this query
    cache_key = db_cache.get_articles_cache_key(
        page=page, limit=limit, category=category, tag=tag, 
        search_query=search_query, sort_by=sort_by
    )
    
    # Try to get from cache first (only for non-search queries to avoid stale search results)
    if not search_query and cache_key:
        cached_result = db_cache.get_cached_articles(cache_key)
        if cached_result:
            logger.debug(f"📦 Cache hit for articles query: page={page}, category={category}, tag={tag}")
            return cached_result
    
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            if search_query:
                # Search in title, summary, AND tags for better results
                where_conditions.append("(title LIKE ? OR summary LIKE ? OR tags LIKE ?)")
                search_term = f"%{search_query}%"
                params.extend([search_term, search_term, search_term])
                
            if category:
                # Categories are now stored as simple strings, not JSON arrays
                # Handle case-insensitive matching for better user experience
                where_conditions.append("LOWER(categories) = LOWER(?)")
                params.append(category)
                logger.info(f"🔍 Filtering by category: '{category}' (case-insensitive)")
                
            if tag:
                # Use enhanced categorization system
                enhanced_condition, enhanced_params = get_enhanced_tag_conditions(tag)
                
                # Special handling for "latest" - add date filter
                if tag.lower() == "latest":
                    # Combine enhanced matching with date filtering
                    date_condition = """(
                        date LIKE '%2025-08%' OR 
                        date LIKE '%Aug 2025%' OR
                        date LIKE '%2025%'
                    )"""
                    final_condition = f"({enhanced_condition} AND {date_condition})"
                    where_conditions.append(final_condition)
                    params.extend(enhanced_params)
                    logger.info(f"🏷️ Enhanced filtering for LATEST tag with {len(enhanced_params)} conditions + date filter")
                else:
                    where_conditions.append(enhanced_condition)
                    params.extend(enhanced_params)
                    logger.info(f"🏷️ Enhanced filtering for '{tag}' with {len(enhanced_params)} conditions (tags + keywords + content)")
                
            if subcategory:
                # Use enhanced categorization for subcategory as well
                enhanced_condition, enhanced_params = get_enhanced_tag_conditions(subcategory)
                where_conditions.append(enhanced_condition)
                params.extend(enhanced_params)
                logger.info(f"🏷️ Enhanced filtering for subcategory '{subcategory}' with {len(enhanced_params)} conditions")
                
            if start_date:
                where_conditions.append("date >= ?")
                params.append(start_date)
                
            if end_date:
                where_conditions.append("date <= ?")
                params.append(end_date)
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Order clause - simplified and reliable date sorting
            if sort_by.upper() == "DESC":
                # For descending order, prioritize 2025 dates first with simpler logic
                order_clause = """ORDER BY 
                    CASE 
                        WHEN date LIKE '%2025%' THEN 1 
                        WHEN date LIKE '%2024%' THEN 2 
                        ELSE 3 
                    END ASC,
                    date DESC, 
                    id DESC"""
            else:
                order_clause = f"ORDER BY date ASC, id ASC"
            
            # Count total articles
            count_query = f"SELECT COUNT(*) FROM articles {where_clause}"
            logger.info(f"🔍 Count query: {count_query} with params: {params}")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            logger.info(f"📊 Found {total} articles matching criteria")
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_pages = (total + limit - 1) // limit
            
            logger.info(f"📄 Pagination: page={page}, limit={limit}, offset={offset}, total={total}, total_pages={total_pages}")
            
            # Get articles
            query = f"""
                SELECT id, title, summary, NULL as content, url, source, date, categories as category, 
                       NULL as subcategory, tags, NULL as image_url, authors as author 
                FROM articles 
                {where_clause} 
                {order_clause} 
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()
            
            # Log the IDs returned for debugging
            returned_ids = [dict(row)['id'] for row in rows]
            logger.info(f"📋 Returned article IDs: {returned_ids}")
            
            # Convert to dictionaries
            articles = []
            for row in rows:
                article = dict(row)
                
                # Clean data - handle None/NULL values for required and optional fields
                # Ensure required fields have proper defaults if None
                if article.get('source') is None or article.get('source') == '':
                    # Set a default source based on category if possible
                    if article.get('category'):
                        if isinstance(article['category'], str) and article['category'].lower() in ["news", "diseases", "solutions", "food"]:
                            article['source'] = f"{article['category'].capitalize()} Information"
                        else:
                            article['source'] = "Health Information Source"
                    else:
                        article['source'] = "Health Information Source"
                
                # Enhanced URL validation - exclude articles with broken URLs
                url = article.get('url', '')
                if not is_valid_article_url(url):
                    logger.warning(f"Skipping article with invalid URL: {url} - Title: {article.get('title', 'Unknown')[:50]}")
                    continue
                
                if article.get('title') is None or article.get('title') == '':
                    article['title'] = 'Untitled'  # Required field
                
                # Clean optional fields - convert empty strings to None
                for optional_field in ['content', 'category', 'subcategory', 'image_url', 'author']:
                    if article.get(optional_field) == '' or article.get(optional_field) == 'NULL':
                        article[optional_field] = None
                
                # Special handling for summary - ensure it's never empty and meaningful
                summary = article.get('summary', '').strip()
                
                # Check if summary is empty, too short, or generic
                # Don't process summaries that are already generated fallbacks
                is_generated_fallback = (
                    summary and (
                        summary.startswith('Important health news:') or
                        summary.startswith('Latest insights on') or
                        summary.startswith('New medical research findings') or
                        summary.startswith('COVID-19 updates and public health') or
                        summary.startswith('Mental health insights') or
                        'Stay informed with the latest from' in summary
                    )
                )
                
                needs_fallback = (
                    not summary or 
                    summary in ['', 'NULL', None] or 
                    len(summary) < 10 or  # Reduced from 20 to 10 - less aggressive
                    (summary.lower() in ['recent developments', 'health news', 'breaking news'] and not is_generated_fallback) or
                    'health article summary' in summary.lower()
                ) and not is_generated_fallback  # Don't regenerate already generated summaries
                
                if needs_fallback:
                    # Generate a more meaningful fallback summary based on title and category
                    title = article.get('title', 'Health Article')
                    category = article.get('category', 'health')
                    source = article.get('source', 'Health News')
                    
                    # Create a more descriptive summary
                    if 'diabetes' in title.lower():
                        article['summary'] = f"Latest insights on diabetes management and treatment options from {source}."
                    elif 'heart' in title.lower() or 'cardiovascular' in title.lower():
                        article['summary'] = f"Important developments in heart health and cardiovascular care from {source}."
                    elif 'nutrition' in title.lower() or 'diet' in title.lower():
                        article['summary'] = f"New findings on nutrition and dietary recommendations from {source}."
                    elif 'mental health' in title.lower():
                        article['summary'] = f"Mental health insights and wellness strategies from {source}."
                    elif 'covid' in title.lower() or 'pandemic' in title.lower():
                        article['summary'] = f"COVID-19 updates and public health information from {source}."
                    elif 'research' in title.lower() or 'study' in title.lower():
                        article['summary'] = f"New medical research findings and healthcare study results from {source}."
                    else:
                        # Generic but more informative fallback
                        if len(title) > 80:
                            article['summary'] = f"{title[:77]}... - Read more about this health development from {source}."
                        else:
                            article['summary'] = f"Important health news: {title}. Stay informed with the latest from {source}."
                    
                    logger.info(f"Generated enhanced fallback summary for article {article.get('id')}: {article['summary'][:50]}...")
                else:
                    # Clean and enhance existing summary
                    if summary:
                        import re
                        # Remove source references like "Source: XYZ" or "(Source: XYZ)" from the summary
                        summary = re.sub(r'\(Source:.*?\)', '', summary)
                        summary = re.sub(r'Source:.*?(\.|$)', '', summary)
                        summary = re.sub(r'\(From:.*?\)', '', summary)
                        summary = re.sub(r'From:.*?(\.|$)', '', summary)
                        
                        # Clean up generic phrases
                        summary = re.sub(r'recent developments?\.?', 'new updates', summary, flags=re.IGNORECASE)
                        summary = re.sub(r'breaking news\.?', 'latest information', summary, flags=re.IGNORECASE)
                        
                        # Ensure proper sentence ending
                        summary = summary.strip()
                        if summary and not summary.endswith(('.', '!', '?', '...')):
                            summary += '.'
                        
                        article['summary'] = summary
                
                # Ensure tags is always a meaningful list
                tags = article.get('tags', '')
                if not tags or tags in ['', 'NULL', None] or tags.lower() in ['recent developments', 'general']:
                    # Generate meaningful tags based on title and content
                    title = article.get('title', '').lower()
                    category = article.get('category', '').lower()
                    source = article.get('source', '').lower()
                    
                    generated_tags = []
                    
                    # Health condition tags
                    if any(word in title for word in ['diabetes', 'diabetic']):
                        generated_tags.extend(['diabetes', 'blood sugar', 'endocrinology'])
                    if any(word in title for word in ['heart', 'cardiac', 'cardiovascular']):
                        generated_tags.extend(['heart health', 'cardiovascular', 'cardiology'])
                    if any(word in title for word in ['mental health', 'depression', 'anxiety']):
                        generated_tags.extend(['mental health', 'wellness', 'psychology'])
                    if any(word in title for word in ['nutrition', 'diet', 'food']):
                        generated_tags.extend(['nutrition', 'diet', 'healthy eating'])
                    if any(word in title for word in ['cancer', 'tumor', 'oncology']):
                        generated_tags.extend(['cancer', 'oncology', 'treatment'])
                    if any(word in title for word in ['covid', 'coronavirus', 'pandemic']):
                        generated_tags.extend(['covid-19', 'pandemic', 'public health'])
                    if any(word in title for word in ['vaccine', 'vaccination', 'immunization']):
                        generated_tags.extend(['vaccination', 'immunization', 'prevention'])
                    
                    # Research and news type tags
                    if any(word in title for word in ['study', 'research', 'trial']):
                        generated_tags.append('medical research')
                    if any(word in title for word in ['breakthrough', 'discovery']):
                        generated_tags.append('breakthrough research')
                    if any(word in title for word in ['treatment', 'therapy']):
                        generated_tags.append('treatment')
                    if any(word in title for word in ['prevention', 'preventive']):
                        generated_tags.append('prevention')
                    
                    # Source-based tags
                    if 'who' in source:
                        generated_tags.append('global health')
                    if 'cdc' in source or 'nih' in source:
                        generated_tags.append('public health')
                    
                    # Category-based fallback
                    if not generated_tags:
                        if 'health' in category:
                            generated_tags = ['health news', 'wellness']
                        elif 'medical' in category:
                            generated_tags = ['medical news', 'healthcare']
                        else:
                            generated_tags = ['health', 'news']
                    
                    # Convert to string format that the database expects
                    article['tags'] = ', '.join(list(set(generated_tags)))
                elif isinstance(tags, str):
                    # Clean existing tags
                    tags = tags.replace('recent developments', 'health updates')
                    tags = tags.replace('general', 'health news')
                    article['tags'] = tags
                else:
                    article['tags'] = []
                
                # Parse categories if they're stored as JSON string
                if article.get('category'):
                    try:
                        if isinstance(article['category'], str):
                            categories_list = json.loads(article['category'])
                            # For backward compatibility, use the first category as 'category'
                            if categories_list and len(categories_list) > 0:
                                article['category'] = categories_list[0]
                            else:
                                article['category'] = None
                    except (json.JSONDecodeError, TypeError):
                        # If it's not JSON, keep as is
                        pass
                
                # Parse tags - handle both JSON arrays and comma-separated strings
                if article.get('tags'):
                    try:
                        if isinstance(article['tags'], str):
                            # First try to parse as JSON
                            try:
                                article['tags'] = json.loads(article['tags'])
                                # Convert underscores back to spaces for frontend compatibility
                                article['tags'] = [tag.replace("_", " ") if isinstance(tag, str) else tag for tag in article['tags']]
                            except (json.JSONDecodeError, TypeError):
                                # If JSON parsing fails, treat as comma-separated string
                                if article['tags'].strip():
                                    article['tags'] = [tag.strip().replace("_", " ") for tag in article['tags'].split(',') if tag.strip()]
                                else:
                                    article['tags'] = []
                        elif isinstance(article['tags'], list):
                            # Already a list, just clean up underscores
                            article['tags'] = [tag.replace("_", " ") if isinstance(tag, str) else tag for tag in article['tags']]
                    except Exception as e:
                        logger.warning(f"Error parsing tags for article {article.get('id')}: {e}")
                        article['tags'] = []
                else:
                    article['tags'] = []
                    
                # Parse date
                if article.get('date'):
                    try:
                        article['date'] = datetime.fromisoformat(article['date'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        article['date'] = datetime.now()
                        
                articles.append(article)
            
            result = {
                "articles": articles,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
            
            # Cache the result (only for non-search queries)
            if not search_query and cache_key:
                db_cache.cache_articles_result(cache_key, result, ttl=180)  # Cache for 3 minutes
                logger.debug(f"💾 Cached articles query result: page={page}, category={category}, tag={tag}")
            
            return result
            
    except Exception as e:
        logger.error(f"Error in get_articles_paginated_optimized: {e}")
        return {
            "articles": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False
        }

@cached(ttl=300, key_prefix="category_stats_")
def get_category_stats_cached() -> Dict[str, int]:
    """Get cached category statistics with improved caching"""
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT categories, COUNT(*) as count 
                FROM articles 
                WHERE categories IS NOT NULL AND categories != '' 
                GROUP BY categories
            """)
            
            category_stats = {}
            for row in cursor.fetchall():
                categories_json = row['categories']
                if categories_json:
                    try:
                        # Parse the JSON array of categories
                        if isinstance(categories_json, str):
                            categories_list = json.loads(categories_json)
                        else:
                            categories_list = categories_json
                        
                        # Count each category
                        for category in categories_list:
                            if category in category_stats:
                                category_stats[category] += row['count']
                            else:
                                category_stats[category] = row['count']
                    except (json.JSONDecodeError, TypeError):
                        # If it's not JSON, treat as single category
                        category_stats[categories_json] = row['count']
                
            _stats_cache['categories'] = category_stats
            _cache_timestamp = datetime.now()
            
            return category_stats
            
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        return {}

def get_cached_stats() -> Dict:
    """Get cached general statistics"""
    global _stats_cache, _cache_timestamp
    
    # Cache for 5 minutes
    if _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < 300:
        return _stats_cache.get('general', {})
    
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total articles
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            # Recent articles (last 7 days)
            cursor.execute("SELECT COUNT(*) FROM articles WHERE date > date('now', '-7 days')")
            recent_articles = cursor.fetchone()[0]
            
            # Total sources
            cursor.execute("SELECT COUNT(DISTINCT source) FROM articles")
            total_sources = cursor.fetchone()[0]
            
            # Category stats
            category_stats = get_category_stats_cached()
            
            stats = {
                "total_articles": total_articles,
                "recent_articles_7_days": recent_articles,
                "total_sources": total_sources,
                "total_categories": len(category_stats),
                "category_distribution": dict(list(category_stats.items())[:10]),
                "last_updated": datetime.now().isoformat()
            }
            
            _stats_cache['general'] = stats
            _cache_timestamp = datetime.now()
            
            return stats
            
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "total_articles": 0,
            "recent_articles_7_days": 0,
            "total_sources": 0,
            "total_categories": 0,
            "category_distribution": {},
            "last_updated": datetime.now().isoformat()
        }

def get_articles_by_ids(article_ids: List[int]) -> List[Dict]:
    """Get multiple articles by their IDs"""
    if not article_ids:
        return []
        
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create placeholders for IN clause
            placeholders = ','.join(['?'] * len(article_ids))
            query = f"""
                SELECT id, title, summary, NULL as content, url, source, date, categories as category, 
                       NULL as subcategory, tags, NULL as image_url, authors as author 
                FROM articles 
                WHERE id IN ({placeholders})
                ORDER BY date DESC
            """
            
            cursor.execute(query, article_ids)
            rows = cursor.fetchall()
            
            articles = []
            for row in rows:
                article = dict(row)
                
                # Parse categories if they're stored as JSON string
                if article.get('category'):
                    try:
                        if isinstance(article['category'], str):
                            categories_list = json.loads(article['category'])
                            # For backward compatibility, use the first category as 'category'
                            if categories_list and len(categories_list) > 0:
                                article['category'] = categories_list[0]
                            else:
                                article['category'] = None
                    except (json.JSONDecodeError, TypeError):
                        # If it's not JSON, keep as is
                        pass
                
                # Parse tags if they're stored as JSON string
                if article.get('tags'):
                    try:
                        if isinstance(article['tags'], str):
                            article['tags'] = json.loads(article['tags'])
                    except (json.JSONDecodeError, TypeError):
                        article['tags'] = []
                else:
                    article['tags'] = []
                    
                # Parse date
                if article.get('date'):
                    try:
                        article['date'] = datetime.fromisoformat(article['date'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        article['date'] = datetime.now()
                        
                articles.append(article)
            
            return articles
            
    except Exception as e:
        logger.error(f"Error getting articles by IDs: {e}")
        return []

def initialize_optimizations():
    """Initialize database optimizations"""
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create indexes if they don't exist
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date)",
                "CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles(categories)",
                "CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)",
                "CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title)",
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                
            conn.commit()
            logger.info("Database indexes initialized successfully")
            
    except Exception as e:
        logger.error(f"Error initializing optimizations: {e}")

def get_all_tags() -> List[str]:
    """Get all unique tags from the database"""
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all non-null tags
            cursor.execute("SELECT DISTINCT tags FROM articles WHERE tags IS NOT NULL AND tags != '' AND tags != '[]'")
            rows = cursor.fetchall()
            
            # Parse JSON tags and collect unique ones
            all_tags = set()
            for row in rows:
                try:
                    if row[0]:
                        tags = json.loads(row[0])
                        if isinstance(tags, list):
                            # Convert underscores back to spaces for frontend compatibility
                            formatted_tags = [tag.replace("_", " ") if isinstance(tag, str) else tag for tag in tags]
                            all_tags.update(formatted_tags)
                except (json.JSONDecodeError, TypeError):
                    continue
            
            return sorted(list(all_tags))
            
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        return []

@lru_cache(maxsize=1)
def get_tags_cached() -> List[str]:
    """Get cached list of all tags"""
    return get_all_tags()

def search_articles_optimized(
    query: str,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "desc",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """
    Optimized search for articles
    """
    return get_articles_paginated_optimized(
        page=page,
        limit=limit,
        sort_by=sort_by,
        search_query=query,
        start_date=start_date,
        end_date=end_date
    )

def get_all_categories() -> List[Dict]:
    """Get all available categories with article counts"""
    try:
        category_stats = get_category_stats_cached()
        categories = []
        
        for category, count in category_stats.items():
            categories.append({
                "name": category,
                "article_count": count
            })
        
        # Sort by article count descending
        categories.sort(key=lambda x: x["article_count"], reverse=True)
        
        return categories
        
    except Exception as e:
        logger.error(f"Error getting all categories: {e}")
        return []

def get_api_statistics() -> Dict:
    """Get comprehensive API statistics"""
    try:
        stats = get_cached_stats()
        tags = get_all_tags()
        categories = get_all_categories()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                **stats,
                "total_tags": len(tags),
                "available_categories": len(categories)
            },
            "categories": categories[:10],  # Top 10 categories
            "sample_tags": tags[:20] if tags else []  # First 20 tags
        }
        
    except Exception as e:
        logger.error(f"Error getting API statistics: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# Initialize on import
try:
    initialize_optimizations()
    # Pre-load categories
    get_cached_category_keywords()
except Exception as e:
    logger.warning(f"Could not initialize optimizations: {e}")
