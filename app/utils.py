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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Frontend menu mapping for category-subcategory consistency
CATEGORY_SUBCATEGORY_MAP = {
    "news": ["latest", "policy and regulation", "govt schemes", "international"],
    "diseases": ["diabetes", "obesity", "inflammation", "cardiovascular", "liver", "kidney", 
                "thyroid", "metabolic", "sleep disorders", "skin", "eyes and ears", "reproductive health"],
    "solutions": ["nutrition", "fitness", "lifestyle", "wellness", "prevention"],
    "food": ["natural food", "organic food", "processed food", "fish and seafood", "food safety"],
    "audience": ["women", "men", "children", "teenagers", "seniors", "athletes", "families"],
    "trending": ["gut health", "mental health", "hormones", "addiction", "sleep health", "sexual wellness"],
    "blogs_and_opinions": []
}

# Database path - adjusted for new structure
DB_PATH = str(Path(__file__).parent.parent / "data" / "articles.db")

# Fallback to old path if new doesn't exist
if not Path(DB_PATH).exists():
    DB_PATH = str(Path(__file__).parent.parent / "db" / "articles.db")

# Path to the consolidated configuration YAML file
CATEGORY_YAML_PATH = Path(__file__).parent.parent / "config" / "config.yml"
# Category keywords file path
CATEGORY_YAML_PATH = Path(__file__).parent.parent / "config" / "config.yml"

def validate_subcategory_for_category(subcategory: str, category: str) -> Optional[str]:
    """
    Validates and corrects subcategory assignment based on main category
    """
    if not subcategory or not category:
        return None
    
    category = category.lower().strip()
    subcategory = subcategory.lower().strip()
    
    # Get valid subcategories for this category
    valid_subcategories = CATEGORY_SUBCATEGORY_MAP.get(category, [])
    
    # If no valid subcategories defined for this category, return None
    if not valid_subcategories:
        return None
    
    # Direct match
    if subcategory in [sub.lower() for sub in valid_subcategories]:
        # Return the properly formatted version
        for valid_sub in valid_subcategories:
            if valid_sub.lower() == subcategory:
                return valid_sub
    
    # Fuzzy matching for common variations
    subcategory_mappings = {
        # News variations
        "breaking news": "latest",
        "latest news": "latest", 
        "govt schemes": "govt schemes",
        "government schemes": "govt schemes",
        "policy": "policy and regulation",
        "regulation": "policy and regulation",
        
        # Diseases variations
        "heart": "cardiovascular",
        "cardiac": "cardiovascular", 
        "blood sugar": "diabetes",
        "weight": "obesity",
        "mental": "sleep disorders",  # Close enough
        "neurological": "sleep disorders",
        "eye": "eyes and ears",
        "ear": "eyes and ears",
        
        # Solutions variations
        "diet": "nutrition",
        "exercise": "fitness",
        "workout": "fitness",
        "health": "wellness",
        
        # Food variations
        "organic": "organic food",
        "seafood": "fish and seafood",
        
        # Audience variations
        "woman": "women",
        "man": "men", 
        "child": "children",
        "teen": "teenagers",
        "elderly": "seniors",
        "senior": "seniors",
        
        # Trending variations
        "gut": "gut health",
        "mental health": "mental health",
        "hormone": "hormones",
        "sleep": "sleep health",
        "sexual": "sexual wellness"
    }
    
    # Check if subcategory matches any mapping
    mapped_subcategory = subcategory_mappings.get(subcategory)
    if mapped_subcategory and mapped_subcategory in valid_subcategories:
        return mapped_subcategory
    
    # If no valid mapping found, return None (will be filtered out)
    return None

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

def _generate_smart_summary(title: str, category: Optional[str] = None, source: Optional[str] = None) -> str:
    """
    Generate a meaningful summary from the title and context when no good summary exists.
    Ensures the summary is always unique and different from the title.
    """
    if not title:
        return "Health and wellness information from medical experts."
    
    # Clean title for processing
    clean_title = title
    if source:
        clean_title = clean_title.replace(source, "").strip()
        clean_title = re.sub(r'^[:\-\s]+', '', clean_title)  # Remove leading punctuation
        clean_title = re.sub(r'[:\-\s]+$', '', clean_title)  # Remove trailing punctuation
    
    # Extract key information from the title itself to create contextual summaries
    title_lower = clean_title.lower()
    
    # Advanced topic-specific summary generation
    if any(keyword in title_lower for keyword in ['diabetes', 'blood sugar', 'insulin', 'glucose']):
        if 'type 2' in title_lower:
            return "Comprehensive information about Type 2 diabetes management, including dietary approaches, medication options, lifestyle modifications, and long-term health outcomes for better glucose control."
        elif 'prevention' in title_lower:
            return "Evidence-based strategies for diabetes prevention, focusing on lifestyle interventions, dietary modifications, physical activity recommendations, and risk factor management."
        else:
            return "Detailed diabetes information covering blood sugar management, treatment protocols, dietary guidelines, and lifestyle strategies for optimal metabolic health and disease control."
    
    elif any(keyword in title_lower for keyword in ['cancer', 'tumor', 'oncology', 'chemotherapy']):
        if 'breast' in title_lower:
            return "Important breast cancer information including screening guidelines, treatment advances, surgical options, recovery support, and preventive measures for women's health."
        elif 'lung' in title_lower:
            return "Lung cancer updates covering early detection methods, treatment innovations, survival rates, prevention strategies, and patient care advancements."
        elif 'prevention' in title_lower:
            return "Cancer prevention strategies including lifestyle modifications, dietary recommendations, screening protocols, and risk reduction techniques based on current medical research."
        else:
            return "Comprehensive cancer information covering treatment advances, patient care strategies, research breakthroughs, and supportive care approaches for improved outcomes."
    
    elif any(keyword in title_lower for keyword in ['heart', 'cardiovascular', 'cardiac', 'stroke']):
        if 'prevention' in title_lower:
            return "Heart disease prevention strategies including dietary modifications, exercise recommendations, risk factor management, and lifestyle changes for cardiovascular health."
        else:
            return "Cardiovascular health information covering heart disease management, treatment options, preventive measures, and lifestyle recommendations for optimal cardiac function."
    
    elif any(keyword in title_lower for keyword in ['vaccine', 'vaccination', 'immunization']):
        return "Vaccination information including safety profiles, efficacy data, immunization schedules, public health recommendations, and evidence-based guidance from health authorities."
    
    elif any(keyword in title_lower for keyword in ['nutrition', 'diet', 'food', 'eating']):
        if 'weight loss' in title_lower or 'obesity' in title_lower:
            return "Nutritional guidance for weight management including evidence-based dietary strategies, meal planning approaches, and sustainable lifestyle changes for healthy weight maintenance."
        else:
            return "Evidence-based nutritional information covering dietary recommendations, food choices, nutrient requirements, and eating strategies for optimal health and wellness."
    
    elif any(keyword in title_lower for keyword in ['mental health', 'depression', 'anxiety', 'stress']):
        return "Mental health resources including treatment approaches, coping strategies, therapeutic options, lifestyle interventions, and professional support for emotional wellbeing."
    
    elif any(keyword in title_lower for keyword in ['covid', 'coronavirus', 'pandemic']):
        return "COVID-19 health information including prevention guidelines, treatment updates, safety protocols, vaccination data, and public health recommendations from medical experts."
    
    elif any(keyword in title_lower for keyword in ['obesity', 'weight', 'overweight']):
        return "Weight management information covering obesity prevention, treatment approaches, lifestyle interventions, dietary strategies, and long-term health outcomes."
    
    elif any(keyword in title_lower for keyword in ['research', 'study', 'clinical trial']):
        return "Medical research findings with clinical implications, study methodologies, evidence analysis, and potential impacts on patient care and treatment protocols."
    
    elif any(keyword in title_lower for keyword in ['exercise', 'fitness', 'physical activity']):
        return "Fitness and exercise information including workout recommendations, physical activity guidelines, health benefits, and strategies for maintaining an active lifestyle."
    
    elif any(keyword in title_lower for keyword in ['gut health', 'microbiome', 'digestive']):
        return "Digestive health information covering gut microbiome research, probiotic benefits, dietary influences on digestion, and strategies for optimal gastrointestinal wellness."
    
    elif any(keyword in title_lower for keyword in ['sleep', 'insomnia', 'sleep disorder']):
        return "Sleep health guidance including sleep hygiene practices, insomnia treatment options, sleep disorder management, and strategies for improving sleep quality and duration."
    
    # Source-specific contextual summaries
    if source:
        source_lower = source.lower()
        if 'who' in source_lower:
            return "World Health Organization health guidance providing international health standards, disease surveillance updates, and global health policy recommendations for public health protection."
        elif 'cdc' in source_lower:
            return "Centers for Disease Control health information offering disease prevention guidelines, public health recommendations, and evidence-based strategies for community health protection."
        elif 'nih' in source_lower:
            return "National Institutes of Health research insights presenting medical breakthroughs, clinical study results, and scientific advances in healthcare and disease treatment."
        elif 'webmd' in source_lower:
            return "Medical information and health guidance providing patient-focused explanations, treatment options, symptom analysis, and healthcare decision support for consumers."
        elif 'harvard' in source_lower:
            return "Harvard Medical School health insights offering evidence-based medical information, research findings, and expert clinical perspectives for informed healthcare decisions."
    
    # Category-based contextual summaries
    if category:
        category_lower = category.lower()
        if category_lower == 'diseases':
            return "Medical condition information providing comprehensive details about symptoms, diagnosis procedures, treatment approaches, management strategies, and patient care guidelines."
        elif category_lower in ['food', 'nutrition']:
            return "Nutritional guidance offering science-based dietary recommendations, food safety information, meal planning strategies, and evidence-based approaches to healthy eating."
        elif category_lower == 'solutions':
            return "Health solutions presenting therapeutic approaches, treatment innovations, preventive strategies, and evidence-based interventions for improved health outcomes."
        elif category_lower == 'news':
            return "Health news updates covering medical developments, research breakthroughs, policy changes, and healthcare innovations affecting patient care and public health."
        elif category_lower == 'trending':
            return "Current health trends featuring emerging research topics, innovative treatments, wellness developments, and evolving healthcare practices gaining scientific attention."
    
    # Advanced fallback based on title analysis
    words = clean_title.split()
    meaningful_words = [word for word in words if len(word) > 3 and word.lower() not in 
                       ['that', 'this', 'with', 'from', 'have', 'been', 'they', 'their', 'will', 'said', 'more', 'than', 'other', 'when', 'what', 'about']]
    
    if len(meaningful_words) >= 2:
        key_concepts = ' '.join(meaningful_words[:3]).lower()
        return f"Health information providing medical insights and evidence-based guidance related to {key_concepts}, including treatment considerations, prevention strategies, and clinical recommendations for improved health outcomes."
    
    # Ultimate fallback with variety
    fallback_summaries = [
        "Medical information and health guidance from healthcare professionals providing evidence-based insights for informed healthcare decisions and improved wellness outcomes.",
        "Health insights covering clinical developments, treatment approaches, and medical research findings to support better health understanding and patient care.",
        "Healthcare information presenting medical expertise, treatment options, and health recommendations based on current clinical evidence and professional standards.",
        "Medical guidance offering health-focused information, clinical insights, and evidence-based recommendations for optimal health management and disease prevention."
    ]
    
    # Use title length to pick a consistent but varied fallback
    index = len(title) % len(fallback_summaries)
    return fallback_summaries[index]

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
                config_data = yaml.safe_load(file) or {}
                _category_cache = config_data.get('categories', {})
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
    Optimized paginated article retrieval with search and filtering
    """
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            if search_query:
                # Enhanced search with relevance scoring and category prioritization
                search_term = f"%{search_query.lower()}%"
                
                # Define category-specific keywords for better matching
                category_keywords = {
                    'food': ['food', 'nutrition', 'diet', 'eating', 'meal', 'recipe', 'ingredient', 'cooking', 'organic', 'superfood'],
                    'fitness': ['exercise', 'workout', 'fitness', 'training', 'gym', 'cardio', 'strength', 'muscle', 'athletic'],
                    'mental_health': ['mental', 'depression', 'anxiety', 'stress', 'psychology', 'therapy', 'mindfulness'],
                    'diseases': ['diabetes', 'cancer', 'heart disease', 'obesity', 'cardiovascular', 'illness', 'condition'],
                    'nutrition': ['vitamin', 'mineral', 'supplement', 'nutrient', 'protein', 'carb', 'fat', 'calorie']
                }
                
                # Check if search term matches category-specific keywords
                matched_categories = []
                query_lower = search_query.lower()
                for cat, keywords in category_keywords.items():
                    if any(keyword in query_lower for keyword in keywords):
                        matched_categories.append(cat)
                
                if matched_categories:
                    # Priority search: prioritize matching categories
                    category_conditions = []
                    for cat in matched_categories:
                        category_conditions.append("categories = ?")
                        params.append(cat)
                    
                    # Enhanced search with category prioritization and relevance scoring
                    where_conditions.append(f"""(
                        (title LIKE ? OR summary LIKE ? OR tags LIKE ?) OR
                        ({' OR '.join(category_conditions)}) OR
                        (tags LIKE ? AND categories IN ({','.join(['?' for _ in matched_categories])}))
                    )""")
                    params.extend([search_term, search_term, search_term, search_term] + matched_categories)
                else:
                    # Standard search if no category match
                    where_conditions.append("(title LIKE ? OR summary LIKE ? OR tags LIKE ?)")
                    params.extend([search_term, search_term, search_term])
                
            if category:
                # Special handling for trending category - show recent articles with trending tags OR trending category
                if category.lower() == "trending":
                    # Use last 7 days to ensure we have content (today's date shown in results anyway)
                    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    # Trending tags from frontend menu + current health trends
                    trending_tags = [
                        "gut health", "mental health", "hormones", "addiction", 
                        "sleep health", "sexual wellness", "microbiome", 
                        "probiotics", "weight loss", "longevity", "wellness",
                        "trending", "viral health", "health trends", "mental health trends"
                    ]
                    
                    # Build OR condition for trending tags
                    tag_conditions = []
                    tag_params = []
                    for tag in trending_tags:
                        tag_conditions.append("tags LIKE ?")
                        tag_params.append(f'%"{tag}"%')
                    
                    # Combine trending category OR trending tags with recent date filter
                    trending_condition = f"(categories LIKE ? OR categories LIKE ? OR categories = ? OR ({' OR '.join(tag_conditions)}))"
                    where_conditions.append(f"date >= ? AND {trending_condition}")
                    
                    # Parameters: date filter + category filters + tag filters
                    category_params = [f'%"{category}"%', f'%{category}%', category]
                    params.extend([week_ago] + category_params + tag_params)
                    
                    logger.info(f"🔥 Trending category: filtering articles from {week_ago} to {today} with trending category OR trending tags")
                else:
                    # Handle both JSON array format ["category"] and plain text format category
                    # Search for both quoted (JSON) and unquoted (plain text) formats
                    where_conditions.append("(categories LIKE ? OR categories LIKE ? OR categories = ?)")
                    params.extend([f'%"{category}"%', f'%{category}%', category])
                    logger.info(f"📂 Filtering by category: '{category}' (checking both JSON and plain text formats)")
                
            if tag and (not category or category.lower() != "trending"):
                # Since tags is stored as JSON array, we need to search within it
                # Handle both frontend format (with spaces) and database format (with underscores)
                # Skip tag filtering when in trending mode as trending has its own tag logic
                tag_underscore = tag.replace(" ", "_")
                
                # Special handling for "latest" - also search for related terms
                if tag.lower() == "latest":
                    where_conditions.append("(tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ?)")
                    params.extend([f'%"{tag}"%', f'%"{tag_underscore}"%', f'%"breaking_news"%', f'%"recent_developments"%', f'%"indian_health_news"%', f'%"trending"%', f'%"smartnews_aggregated"%'])
                    logger.info(f" Filtering by tag: '{tag}' (also checking related terms: breaking_news, recent_developments, trending, smartnews_aggregated)")
                # Special handling for "lifestyle" - also search for related terms
                elif tag.lower() == "lifestyle":
                    where_conditions.append("(tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ?)")
                    params.extend([f'%"{tag}"%', f'%"{tag_underscore}"%', f'%"lifestyle_changes"%', f'%"health_lifestyle"%', f'%"wellness"%'])
                    logger.info(f" Filtering by tag: '{tag}' (also checking related terms: lifestyle_changes, health_lifestyle, wellness)")
                else:
                    where_conditions.append("(tags LIKE ? OR tags LIKE ?)")
                    params.extend([f'%"{tag}"%', f'%"{tag_underscore}"%'])
                    logger.info(f" Filtering by tag: '{tag}' (also checking '{tag_underscore}')")
                
            if subcategory:
                # Search in both subcategory field and tags field for backward compatibility
                subcategory_underscore = subcategory.replace(" ", "_")
                where_conditions.append("(subcategory LIKE ? OR subcategory LIKE ? OR tags LIKE ? OR tags LIKE ?)")
                params.extend([f'%"{subcategory}"%', f'%"{subcategory_underscore}"%', f'%"{subcategory}"%', f'%"{subcategory_underscore}"%'])
                logger.info(f" Filtering by subcategory: '{subcategory}' (also checking tags and '{subcategory_underscore}')")
                
            # Apply general date filters only if not trending category (trending has its own date logic)
            if start_date and (not category or category.lower() != "trending"):
                where_conditions.append("date >= ?")
                params.append(start_date)
                
            if end_date and (not category or category.lower() != "trending"):
                where_conditions.append("date <= ?")
                params.append(end_date)
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Order clause - prioritize relevance for search queries
            if search_query:
                # For search queries, prioritize relevance with date as secondary sort
                if sort_by.upper() == "DESC":
                    order_clause = f"""ORDER BY 
                        CASE 
                            WHEN title LIKE '%{search_query.lower()}%' THEN 1
                            WHEN summary LIKE '%{search_query.lower()}%' THEN 2
                            WHEN tags LIKE '%{search_query.lower()}%' THEN 3
                            ELSE 4
                        END,
                        date DESC, id DESC"""
                else:
                    order_clause = f"""ORDER BY 
                        CASE 
                            WHEN title LIKE '%{search_query.lower()}%' THEN 1
                            WHEN summary LIKE '%{search_query.lower()}%' THEN 2
                            WHEN tags LIKE '%{search_query.lower()}%' THEN 3
                            ELSE 4
                        END,
                        date ASC, id ASC"""
            else:
                # For non-search queries, use date ordering
                if sort_by.upper() == "DESC":
                    order_clause = f"ORDER BY date DESC, id DESC"
                else:
                    order_clause = f"ORDER BY date ASC, id ASC"
            
            # Count total articles (using DISTINCT to avoid duplicates)
            count_query = f"SELECT COUNT(DISTINCT id) FROM articles {where_clause}"
            logger.info(f" Count query: {count_query} with params: {params}")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            logger.info(f" Found {total} articles matching criteria")
            
            # Calculate pagination
            offset = (page - 1) * limit
            total_pages = (total + limit - 1) // limit
            
            logger.info(f"📄 Pagination: page={page}, limit={limit}, offset={offset}, total={total}, total_pages={total_pages}")
            
            # Get articles (using DISTINCT to prevent duplicates)
            query = f"""
                SELECT DISTINCT id, title, summary, NULL as content, url, source, date, categories as category, 
                       subcategory, tags, NULL as image_url, authors as author 
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
                if article.get('url') is None or article.get('url') == '':
                    article['url'] = ''  # Required field, use empty string as fallback
                if article.get('title') is None or article.get('title') == '':
                    article['title'] = 'Untitled'  # Required field
                
                # Clean optional fields - convert empty strings to None
                for optional_field in ['content', 'category', 'subcategory', 'image_url', 'author']:
                    if article.get(optional_field) == '' or article.get(optional_field) == 'NULL':
                        article[optional_field] = None
                
                # Special handling for summary - preserve actual scraped content summaries
                summary = article.get('summary', '')
                title = article.get('title', '')
                
                # Clean summary text by removing source references and generic patterns
                if summary and summary not in ['', 'NULL', None]:
                    import re
                    # Remove source references like "Source: XYZ" or "(Source: XYZ)" from the summary
                    summary = re.sub(r'\(Source:.*?\)', '', summary)
                    summary = re.sub(r'Source:.*?(\.|$)', '', summary)
                    summary = re.sub(r'\(From:.*?\)', '', summary)
                    summary = re.sub(r'From:.*?(\.|$)', '', summary)
                    
                    # Remove trailing/leading punctuation artifacts
                    summary = re.sub(r'^[:\-\s\.]+', '', summary)
                    summary = re.sub(r'[:\-\s\.]+$', '', summary)
                    
                    # Remove news outlet names from the end (common pattern: "Article title News Outlet...")
                    summary = re.sub(r'\s+(FOX\s?\d*|CNN|BBC|Reuters|AP|Associated Press|ABC|CBS|NBC|STAT|Times|Post|News|Today|Daily|Herald|Tribune|Gazette|Chronicle|Journal|Observer|Guardian|Telegraph|Independent|Mirror|Express|Mail)[\s\.]*$', '', summary, flags=re.IGNORECASE)
                    
                    # Remove website domains and URLs
                    summary = re.sub(r'\s+[a-zA-Z0-9-]+\.(com|org|net|edu|gov|co\.uk|in)[\s\.]*$', '', summary, flags=re.IGNORECASE)
                    
                    # Remove trailing dots and website names
                    summary = re.sub(r'\s*\.{3,}$', '', summary)  # Remove trailing ellipsis
                    
                    # Check for titles that are just repeated in summary (very common issue)
                    title_words = set(title.lower().split())
                    summary_words = set(summary.lower().split())
                    
                    # More lenient approach: Only consider it generic if it's EXACTLY the title or very close
                    title_clean = title.lower().strip()
                    summary_clean = summary.lower().strip()
                    
                    # Check if summary is exactly the title or title + source name pattern
                    is_title_duplicate = (
                        summary_clean == title_clean or  # Exact match
                        summary_clean.startswith(title_clean) and len(summary_clean) - len(title_clean) < 30 or  # Title + short source
                        title_clean.startswith(summary_clean) and len(title_clean) - len(summary_clean) < 10  # Summary is truncated title
                    )
                    
                    # If summary has significant unique content, keep it even if it has some title overlap
                    unique_words = summary_words - title_words
                    has_unique_content = len(unique_words) >= 5 and len(summary.split()) >= 8
                    
                    if is_title_duplicate and not has_unique_content:
                        is_generic = True
                    else:
                        # Only check for truly generic or useless summaries
                        generic_patterns = [
                            r'^- Health article summary\.$',
                            r'^Health News Network.*$',
                            r'^Latest health news:.*$',
                            r'^Breaking health news:.*$',
                            r'^Read more.*$',
                            r'^Click here.*$',
                            r'^Learn more.*$',
                            r'^No summary available.*$',
                            r'^Summary not available.*$',
                            r'^.*\s+(FOX|CNN|BBC|Reuters|AP|STAT|News|Times|Daily)[\s\.]*$',  # Ends with news outlet
                            r'^Latest health news and medical developments.*$',  # Generic pattern we saw
                            r'^.*\s+(FOX\s?\d+|ABC|CBS|NBC|MSNBC)[\s\.]*$',  # TV networks
                            r'^.*\.(com|org|net)[\s\.]*$',  # Ends with domain
                            r'^.*\s+\-\s+[A-Z]{2,}[\s\.]*$'  # Ends with - ACRONYM pattern
                        ]
                        
                        is_generic = False
                        
                        # Check for truly generic patterns (more restrictive)
                        for pattern in generic_patterns:
                            if re.match(pattern, summary.strip(), re.IGNORECASE):
                                is_generic = True
                                break
                        
                        # Check if summary is too short to be meaningful (less than 15 characters - lowered threshold)
                        if len(summary.strip()) < 15:
                            is_generic = True
                        
                        # Check if summary is just repeated words or very low information content
                        words = summary.lower().split()
                        if len(set(words)) < len(words) / 3 and len(words) > 5:  # Too much repetition
                            is_generic = True
                    
                    if is_generic:
                        # Only generate fallback for truly bad summaries
                        article['summary'] = _generate_smart_summary(title, article.get('category'), article.get('source'))
                        logger.debug(f"Replaced generic/poor summary for article: {title[:50]}...")
                    else:
                        # Keep the actual scraped summary - this is the real content!
                        summary = summary.strip()
                        
                        # Special case: If it's a Google News article and summary is just title + source,
                        # generate a better summary instead of showing redundant info
                        source = article.get('source', '')
                        if ('google news' in source.lower() and 
                            is_title_duplicate and 
                            not has_unique_content):
                            article['summary'] = _generate_smart_summary(title, article.get('category'), source)
                            logger.debug(f"Generated better summary for Google News article: {title[:50]}...")
                        else:
                            article['summary'] = summary
                        
                else:
                    # Generate fallback for truly empty summaries only
                    article['summary'] = _generate_smart_summary(title, article.get('category'), article.get('source'))
                
                # Ensure tags is always a list
                if not article.get('tags') or article.get('tags') in ['', 'NULL', None]:
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
                
                # Parse tags if they're stored as JSON string
                if article.get('tags'):
                    try:
                        if isinstance(article['tags'], str):
                            article['tags'] = json.loads(article['tags'])
                            # Convert underscores back to spaces for frontend compatibility
                            article['tags'] = [tag.replace("_", " ") if isinstance(tag, str) else tag for tag in article['tags']]
                    except (json.JSONDecodeError, TypeError):
                        article['tags'] = []
                else:
                    article['tags'] = []
                
                # Parse subcategory if it's stored as JSON string
                if article.get('subcategory'):
                    try:
                        if isinstance(article['subcategory'], str):
                            subcategory_list = json.loads(article['subcategory'])
                            # Convert to comma-separated string for frontend compatibility
                            if subcategory_list and len(subcategory_list) > 0:
                                # Convert underscores back to spaces
                                subcategory_list = [sub.replace("_", " ") if isinstance(sub, str) else sub for sub in subcategory_list]
                                article['subcategory'] = ", ".join(subcategory_list)
                            else:
                                article['subcategory'] = None
                    except (json.JSONDecodeError, TypeError):
                        # If it's not JSON, keep as is but clean underscores
                        if isinstance(article['subcategory'], str):
                            article['subcategory'] = article['subcategory'].replace("_", " ")
                else:
                    article['subcategory'] = None
                
                # Validate subcategory against main category
                if article.get('subcategory') and article.get('category'):
                    subcategory_str = str(article['subcategory']) if article['subcategory'] else ""
                    category_str = str(article['category']) if article['category'] else ""
                    
                    if subcategory_str and category_str:
                        validated_subcategory = validate_subcategory_for_category(
                            subcategory_str, 
                            category_str
                        )
                        if validated_subcategory:
                            article['subcategory'] = validated_subcategory
                        else:
                            # Remove invalid subcategory
                            logger.debug(f"Removed invalid subcategory '{subcategory_str}' for category '{category_str}'")
                            article['subcategory'] = None
                    
                # Parse date
                if article.get('date'):
                    try:
                        article['date'] = datetime.fromisoformat(article['date'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        article['date'] = datetime.now()
                        
                articles.append(article)
            
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

def get_category_stats_cached() -> Dict[str, int]:
    """Get cached category statistics"""
    global _stats_cache, _cache_timestamp
    
    # Cache for 5 minutes
    if _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < 300:
        return _stats_cache.get('categories', {})
    
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
                        # If it's not JSON, treat as single category (plain text format)
                        category_name = categories_json.strip()
                        if category_name in category_stats:
                            category_stats[category_name] += row['count']
                        else:
                            category_stats[category_name] = row['count']
                
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


# ============================================================================
# SYSTEM MAINTENANCE AND TESTING UTILITIES
# ============================================================================

def check_category_distribution() -> Dict:
    """Check the current category distribution"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Get category distribution
            cursor.execute('''
                SELECT categories, COUNT(*) as count 
                FROM articles 
                GROUP BY categories 
                ORDER BY count DESC
            ''')
            
            results = cursor.fetchall()
            total = sum(r[1] for r in results)
            
            # Format results
            distribution = {}
            for cat, count in results:
                distribution[cat] = {
                    'count': count,
                    'percentage': round((count / total) * 100, 1) if total > 0 else 0
                }
            
            # Check specific categories of interest
            key_categories = ['blogs_and_opinions', 'food', 'nutrition', 'fitness', 'mental_health']
            key_stats = {}
            for category in key_categories:
                cursor.execute('SELECT COUNT(*) FROM articles WHERE categories = ?', (category,))
                count = cursor.fetchone()[0]
                key_stats[category] = count
            
            return {
                'total_articles': total,
                'distribution': distribution,
                'key_categories': key_stats,
                'status': 'success'
            }
            
    except Exception as e:
        logger.error(f"Error checking category distribution: {e}")
        return {'status': 'error', 'error': str(e)}


def test_search_functionality(search_terms: Optional[List[str]] = None) -> Dict:
    """Test search functionality with various keywords"""
    if search_terms is None:
        search_terms = ['food', 'nutrition', 'fitness', 'diabetes']
    
    try:
        results = {}
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            for search_term in search_terms:
                search_pattern = f'%{search_term}%'
                cursor.execute('''
                    SELECT title, categories, tags
                    FROM articles 
                    WHERE title LIKE ? OR summary LIKE ? OR tags LIKE ? OR categories LIKE ?
                    ORDER BY 
                        CASE 
                            WHEN title LIKE ? THEN 1
                            WHEN summary LIKE ? THEN 2
                            WHEN tags LIKE ? THEN 3
                            ELSE 4
                        END
                    LIMIT 5
                ''', (search_pattern, search_pattern, search_pattern, search_pattern,
                      search_pattern, search_pattern, search_pattern))

                search_results = cursor.fetchall()
                results[search_term] = {
                    'count': len(search_results),
                    'results': [
                        {
                            'title': title[:60] + '...' if len(title) > 60 else title,
                            'category': category,
                            'tags': tags[:50] + '...' if tags and len(tags) > 50 else tags
                        }
                        for title, category, tags in search_results
                    ]
                }
        
        return {'status': 'success', 'search_results': results}
        
    except Exception as e:
        logger.error(f"Error testing search functionality: {e}")
        return {'status': 'error', 'error': str(e)}


def validate_rss_sources(limit: int = 15) -> Dict:
    """Test RSS sources to verify they're working"""
    try:
        import sys
        import requests
        import time
        from pathlib import Path
        
        # Add project root to path for scraper import
        BASE_DIR = Path(__file__).resolve().parent.parent
        sys.path.append(str(BASE_DIR))
        
        from scrapers.scraper import EnhancedHealthScraper
        
        scraper = EnhancedHealthScraper()
        total_sources = len(scraper.rss_sources)
        
        working = 0
        failed = 0
        failed_sources = []
        working_sources = []
        
        for i, source in enumerate(scraper.rss_sources[:limit]):
            try:
                response = requests.get(source['url'], timeout=10)
                if response.status_code == 200:
                    working += 1
                    working_sources.append(source['name'])
                else:
                    failed += 1
                    failed_sources.append({
                        'name': source['name'],
                        'error': f'HTTP {response.status_code}'
                    })
            except Exception as e:
                failed += 1
                failed_sources.append({
                    'name': source['name'],
                    'error': str(e)[:50]
                })
            
            time.sleep(0.3)  # Be respectful
        
        return {
            'status': 'success',
            'total_sources': total_sources,
            'tested': limit,
            'working': working,
            'failed': failed,
            'success_rate': round((working / limit) * 100, 1) if limit > 0 else 0,
            'working_sources': working_sources,
            'failed_sources': failed_sources
        }
        
    except Exception as e:
        logger.error(f"Error validating RSS sources: {e}")
        return {'status': 'error', 'error': str(e)}


def standardize_category_formats() -> Dict:
    """Standardize inconsistent category formats in the database"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Define the mapping from old formats to new formats
            category_mapping = {
                '["diseases"]': 'diseases',
                '["News"]': 'news', 
                '["news"]': 'news',
                '["solutions"]': 'solutions',
                '["audience"]': 'audience',
                '["diseases", "mental_health"]': 'diseases',
                '["solutions", "mental_health"]': 'solutions',
                '["trending"]': 'trending',
                '["blogs_and_opinions"]': 'blogs_and_opinions',
                '["food"]': 'food',
                '["nutrition"]': 'nutrition',
                '["fitness"]': 'fitness'
            }
            
            updates_made = 0
            update_details = []
            
            for old_format, new_format in category_mapping.items():
                cursor.execute('UPDATE articles SET categories = ? WHERE categories = ?', 
                             (new_format, old_format))
                if cursor.rowcount > 0:
                    update_details.append({
                        'old_format': old_format,
                        'new_format': new_format,
                        'count': cursor.rowcount
                    })
                    updates_made += cursor.rowcount
            
            conn.commit()
            
            return {
                'status': 'success',
                'total_updates': updates_made,
                'update_details': update_details,
                'message': 'No category format issues found' if updates_made == 0 else f'Updated {updates_made} articles'
            }
            
    except Exception as e:
        logger.error(f"Error standardizing categories: {e}")
        return {'status': 'error', 'error': str(e)}


def system_health_check() -> Dict:
    """Run a comprehensive system health check"""
    try:
        health_report = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Check database connectivity
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM articles')
                total_articles = cursor.fetchone()[0]
                health_report['checks']['database'] = {
                    'status': 'healthy',
                    'total_articles': total_articles
                }
        except Exception as e:
            health_report['checks']['database'] = {
                'status': 'error',
                'error': str(e)
            }
            health_report['status'] = 'unhealthy'
        
        # Check for duplicate articles
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT title, COUNT(*) as count 
                    FROM articles 
                    GROUP BY title 
                    HAVING count > 1 
                    LIMIT 5
                ''')
                duplicates = cursor.fetchall()
                health_report['checks']['duplicates'] = {
                    'status': 'healthy' if len(duplicates) == 0 else 'warning',
                    'duplicate_count': len(duplicates),
                    'sample_duplicates': [{'title': title, 'count': count} for title, count in duplicates]
                }
        except Exception as e:
            health_report['checks']['duplicates'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Check for articles without categories
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM articles WHERE categories IS NULL OR categories = ""')
                uncategorized = cursor.fetchone()[0]
                health_report['checks']['categorization'] = {
                    'status': 'healthy' if uncategorized == 0 else 'warning',
                    'uncategorized_count': uncategorized
                }
        except Exception as e:
            health_report['checks']['categorization'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Check recent articles
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM articles WHERE date >= date("now", "-7 days")')
                recent_articles = cursor.fetchone()[0]
                health_report['checks']['recent_activity'] = {
                    'status': 'healthy',
                    'recent_articles_7_days': recent_articles
                }
        except Exception as e:
            health_report['checks']['recent_activity'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return health_report
        
    except Exception as e:
        logger.error(f"Error in system health check: {e}")
        return {
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }


def run_comprehensive_system_check() -> Dict:
    """Run all system utilities and return comprehensive report"""
    try:
        report = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Run health check
        report['checks']['health_check'] = system_health_check()
        
        # Check category distribution
        report['checks']['category_distribution'] = check_category_distribution()
        
        # Test search functionality
        report['checks']['search_test'] = test_search_functionality()
        
        # Validate RSS sources (limited to 10 for performance)
        report['checks']['rss_validation'] = validate_rss_sources(limit=10)
        
        # Check if any system is unhealthy
        for check_name, check_result in report['checks'].items():
            if check_result.get('status') == 'error':
                report['status'] = 'warning'
                break
        
        return report
        
    except Exception as e:
        logger.error(f"Error in comprehensive system check: {e}")
        return {
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }
