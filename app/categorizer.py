#!/usr/bin/env python3
"""
Intelligent Article Categorizer
Automatically categorizes health articles into proper categories and subcategories
based on content analysis and keyword matching.
"""

import re
import yaml
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthArticleCategorizer:
    """Intelligent categorizer for health articles"""
    
    def __init__(self):
        self.categories_config = self._load_categories_config()
        self.category_keywords = self._build_keyword_mapping()
        
    def _load_categories_config(self) -> Dict:
        """Load categories configuration from YAML file"""
        try:
            config_path = Path(__file__).parent / "health_categories.yml"
            with open(config_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading categories config: {e}")
            return {}
    
    def _build_keyword_mapping(self) -> Dict[str, List[str]]:
        """Build a flat keyword mapping for efficient categorization"""
        keyword_mapping = {}
        
        for main_category, subcategories in self.categories_config.items():
            if isinstance(subcategories, dict):
                for subcategory, keywords in subcategories.items():
                    if isinstance(keywords, list):
                        # Create entries for both main category and subcategory
                        category_key = f"{main_category}_{subcategory}"
                        keyword_mapping[category_key] = {
                            'keywords': [kw.lower() for kw in keywords],
                            'main_category': main_category,
                            'subcategory': subcategory,
                            'weight': len(keywords)  # More keywords = higher weight
                        }
        
        return keyword_mapping
    
    def categorize_article(self, title: str, summary: str, source_category: str = None) -> Tuple[str, str]:
        """
        Categorize an article based on its title and summary
        
        Args:
            title: Article title
            summary: Article summary/description
            source_category: Original source category (optional)
            
        Returns:
            Tuple of (main_category, subcategory)
        """
        # Combine title and summary for analysis (title gets more weight)
        text_to_analyze = f"{title} {title} {summary}".lower()
        
        # Score each category based on keyword matches
        category_scores = {}
        
        for category_key, category_info in self.category_keywords.items():
            score = 0
            keywords = category_info['keywords']
            
            # Count keyword matches
            for keyword in keywords:
                # Exact phrase matching gets higher score
                if keyword in text_to_analyze:
                    # Title matches get double score
                    title_matches = title.lower().count(keyword)
                    summary_matches = summary.lower().count(keyword)
                    
                    score += (title_matches * 2) + summary_matches
            
            if score > 0:
                # Normalize score by keyword count to avoid bias toward categories with more keywords
                normalized_score = score / len(keywords)
                category_scores[category_key] = {
                    'score': normalized_score,
                    'main_category': category_info['main_category'],
                    'subcategory': category_info['subcategory']
                }
        
        # Find the best matching category
        if category_scores:
            best_match = max(category_scores.items(), key=lambda x: x[1]['score'])
            main_category = best_match[1]['main_category']
            subcategory = best_match[1]['subcategory']
            
            logger.debug(f"Categorized article '{title[:50]}...' as {main_category}/{subcategory} (score: {best_match[1]['score']:.2f})")
            return main_category, subcategory
        
        # Fallback categorization based on source
        if source_category:
            return self._fallback_categorization(source_category, text_to_analyze)
        
        # Default fallback
        return "news", "general"
    
    def _fallback_categorization(self, source_category: str, text: str) -> Tuple[str, str]:
        """Fallback categorization based on source category and basic text analysis"""
        
        # Map source categories to our main categories
        source_mapping = {
            'health_news': ('news', 'general'),
            'health_info': ('solutions', 'general'),
            'medical_advice': ('solutions', 'prevention'),
            'medical_research': ('news', 'research'),
            'public_health': ('news', 'policy'),
        }
        
        if source_category in source_mapping:
            return source_mapping[source_category]
        
        # Basic keyword-based fallback
        if any(word in text for word in ['diabetes', 'blood sugar', 'insulin']):
            return "diseases", "diabetes"
        elif any(word in text for word in ['heart', 'cardiovascular', 'blood pressure']):
            return "diseases", "cardiovascular"
        elif any(word in text for word in ['diet', 'nutrition', 'food']):
            return "nutrition", "general"
        elif any(word in text for word in ['exercise', 'fitness', 'workout']):
            return "fitness", "exercise"
        elif any(word in text for word in ['women', 'pregnancy', 'maternal']):
            return "audience", "women"
        elif any(word in text for word in ['men', 'prostate', 'testosterone']):
            return "audience", "men"
        elif any(word in text for word in ['children', 'pediatric', 'kids']):
            return "audience", "children"
        
        return "news", "general"
    
    def get_category_suggestions(self, text: str, limit: int = 5) -> List[Dict]:
        """Get top category suggestions for given text"""
        text_lower = text.lower()
        suggestions = []
        
        for category_key, category_info in self.category_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in category_info['keywords']:
                if keyword in text_lower:
                    score += text_lower.count(keyword)
                    matched_keywords.append(keyword)
            
            if score > 0:
                suggestions.append({
                    'main_category': category_info['main_category'],
                    'subcategory': category_info['subcategory'],
                    'score': score,
                    'matched_keywords': matched_keywords
                })
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:limit]
    
    def validate_category(self, main_category: str, subcategory: str) -> bool:
        """Validate if a category/subcategory combination exists"""
        if main_category not in self.categories_config:
            return False
        
        subcategories = self.categories_config[main_category]
        if isinstance(subcategories, dict):
            return subcategory in subcategories
        
        return False
    
    def get_all_categories(self) -> Dict[str, List[str]]:
        """Get all available categories and their subcategories"""
        result = {}
        
        for main_category, subcategories in self.categories_config.items():
            if isinstance(subcategories, dict):
                result[main_category] = list(subcategories.keys())
            else:
                result[main_category] = []
        
        return result

# Global categorizer instance
health_categorizer = HealthArticleCategorizer()