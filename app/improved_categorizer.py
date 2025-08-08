#!/usr/bin/env python3
"""
Improved Article Categorizer
Enhanced categorization system for better category and subcategory assignment
"""

import re
import json
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedArticleCategorizer:
    """Enhanced categorizer with better logic for categories, subcategories, and tags"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.category_rules = self._build_category_rules()
        self.subcategory_rules = self._build_subcategory_rules()
        self.tag_standardization = self._build_tag_standardization()
        
    def _build_category_rules(self) -> Dict:
        """Build comprehensive category classification rules"""
        return {
            # NEWS CATEGORY - Current events, policy, breaking news
            'news': {
                'keywords': [
                    # Policy and regulation
                    'health policy', 'government', 'ministry', 'department', 'regulation',
                    'fda approval', 'who announces', 'health ministry', 'cghs', 'ayushman',
                    'policy', 'guideline', 'health scheme', 'government scheme',
                    
                    # Breaking news indicators
                    'breaking', 'announces', 'launches', 'approved', 'emergency',
                    'alert', 'warning', 'outbreak', 'pandemic', 'epidemic',
                    
                    # News sources and formats
                    'health ministry', 'who reports', 'cdc announces', 'nih says',
                    'government says', 'official statement', 'press release'
                ],
                'title_patterns': [
                    r'health ministry', r'government', r'who announces', r'cdc reports',
                    r'fda approves', r'breaking:', r'urgent:', r'alert:'
                ],
                'weight_multiplier': 1.5  # Higher weight for exact matches
            },
            
            # DISEASES CATEGORY - Medical conditions, symptoms, treatments
            'diseases': {
                'keywords': [
                    # Specific diseases
                    'diabetes', 'cardiovascular', 'heart disease', 'hypertension',
                    'obesity', 'cancer', 'alzheimer', 'parkinson', 'stroke',
                    'arthritis', 'asthma', 'copd', 'pneumonia', 'tuberculosis',
                    'hepatitis', 'cirrhosis', 'kidney disease', 'liver disease',
                    
                    # Medical terms
                    'disease', 'syndrome', 'disorder', 'condition', 'infection',
                    'inflammation', 'symptoms', 'diagnosis', 'treatment',
                    'therapy', 'medication', 'drug', 'clinical trial',
                    
                    # Metabolic diseases
                    'metabolic syndrome', 'insulin resistance', 'blood sugar',
                    'cholesterol', 'triglycerides', 'fatty liver'
                ],
                'exclude_patterns': [
                    r'diet', r'nutrition', r'food', r'recipe', r'cooking',
                    r'exercise', r'workout', r'fitness', r'gym'
                ],
                'weight_multiplier': 2.0
            },
            
            # NUTRITION CATEGORY - Food, diet, nutrients
            'nutrition': {
                'keywords': [
                    # Food and diet
                    'nutrition', 'diet', 'food', 'meal', 'recipe', 'cooking',
                    'vitamin', 'mineral', 'supplement', 'nutrient', 'protein',
                    'carbohydrate', 'fat', 'fiber', 'antioxidant', 'omega',
                    
                    # Dietary patterns
                    'mediterranean diet', 'keto', 'paleo', 'vegan', 'vegetarian',
                    'intermittent fasting', 'low carb', 'high protein',
                    
                    # Food types
                    'organic', 'processed food', 'whole grain', 'fruits', 'vegetables',
                    'nuts', 'seeds', 'fish', 'meat', 'dairy'
                ],
                'title_patterns': [
                    r'diet', r'nutrition', r'food', r'vitamin', r'supplement',
                    r'eating', r'meal', r'recipe'
                ],
                'weight_multiplier': 1.8
            },
            
            # FITNESS CATEGORY - Exercise, physical activity
            'fitness': {
                'keywords': [
                    'exercise', 'workout', 'fitness', 'training', 'gym',
                    'cardio', 'strength', 'aerobic', 'yoga', 'pilates',
                    'running', 'walking', 'swimming', 'cycling', 'sports',
                    'physical activity', 'athletics', 'performance'
                ],
                'title_patterns': [
                    r'exercise', r'workout', r'fitness', r'training', r'gym',
                    r'sports', r'running', r'yoga'
                ],
                'weight_multiplier': 2.0
            },
            
            # LIFESTYLE CATEGORY - Wellness, prevention, habits
            'lifestyle': {
                'keywords': [
                    'lifestyle', 'wellness', 'wellbeing', 'healthy living',
                    'prevention', 'preventive', 'self care', 'mindfulness',
                    'meditation', 'stress', 'sleep', 'rest', 'relaxation',
                    'habits', 'routine', 'balance', 'mental health'
                ],
                'weight_multiplier': 1.5
            },
            
            # AUDIENCE CATEGORY - Demographics, gender-specific
            'audience': {
                'keywords': [
                    # Women
                    'women', 'female', 'pregnancy', 'maternal', 'menopause',
                    'menstruation', 'gynecology', 'obstetrics', 'fertility',
                    
                    # Men
                    'men', 'male', 'prostate', 'testosterone', 'erectile',
                    'masculine', 'paternal',
                    
                    # Age groups
                    'children', 'pediatric', 'kids', 'infant', 'teenager',
                    'adolescent', 'elderly', 'senior', 'aging', 'geriatric',
                    
                    # Special populations
                    'athletes', 'pregnancy', 'breastfeeding', 'family'
                ],
                'weight_multiplier': 1.7
            }
        }
    
    def _build_subcategory_rules(self) -> Dict:
        """Build subcategory classification rules"""
        return {
            'news': {
                'latest': ['breaking', 'urgent', 'recent', 'new', 'latest', 'today'],
                'policy_and_regulation': [
                    'health policy', 'government', 'ministry', 'regulation',
                    'fda approval', 'cghs', 'ayushman', 'health scheme',
                    'policy', 'guideline', 'law', 'act', 'bill'
                ],
                'international': [
                    'who', 'global', 'international', 'worldwide', 'pandemic',
                    'epidemic', 'outbreak', 'world health'
                ],
                'govt_schemes': [
                    'government scheme', 'health scheme', 'cghs', 'ayushman bharat',
                    'public health program', 'health insurance'
                ]
            },
            
            'diseases': {
                'diabetes': [
                    'diabetes', 'diabetic', 'blood sugar', 'glucose', 'insulin',
                    'hyperglycemia', 'hypoglycemia', 'type 1', 'type 2'
                ],
                'cardiovascular': [
                    'heart', 'cardiac', 'cardiovascular', 'coronary', 'blood pressure',
                    'hypertension', 'cholesterol', 'stroke', 'heart attack'
                ],
                'obesity': [
                    'obesity', 'obese', 'overweight', 'weight', 'bmi',
                    'weight management', 'bariatric', 'weight loss'
                ],
                'metabolic': [
                    'metabolic syndrome', 'metabolism', 'insulin resistance',
                    'metabolic disorder', 'endocrine', 'hormone'
                ],
                'cancer': [
                    'cancer', 'tumor', 'oncology', 'malignant', 'chemotherapy',
                    'radiation', 'carcinoma', 'leukemia'
                ],
                'mental_health': [
                    'depression', 'anxiety', 'mental health', 'psychiatric',
                    'bipolar', 'stress', 'ptsd'
                ],
                'liver': [
                    'liver', 'hepatic', 'hepatitis', 'cirrhosis', 'fatty liver',
                    'nafld', 'liver disease'
                ],
                'kidney': [
                    'kidney', 'renal', 'dialysis', 'kidney disease', 'nephrology'
                ]
            },
            
            'nutrition': {
                'micronutrients': [
                    'vitamin', 'mineral', 'supplement', 'vitamin d', 'vitamin c',
                    'iron', 'calcium', 'magnesium', 'zinc', 'antioxidant'
                ],
                'macronutrients': [
                    'protein', 'carbohydrate', 'fat', 'fiber', 'amino acid',
                    'fatty acid', 'omega', 'calorie'
                ],
                'food_quality': [
                    'organic', 'processed', 'whole food', 'natural', 'fresh',
                    'artificial', 'preservative', 'additive'
                ],
                'sugar_sweeteners': [
                    'sugar', 'sweetener', 'artificial sweetener', 'corn syrup',
                    'fructose', 'glucose', 'sucrose'
                ],
                'dietary_patterns': [
                    'diet', 'mediterranean', 'keto', 'paleo', 'vegan',
                    'vegetarian', 'intermittent fasting'
                ]
            },
            
            'audience': {
                'women': [
                    'women', 'female', 'pregnancy', 'maternal', 'menopause',
                    'menstruation', 'gynecology', 'fertility', 'breast'
                ],
                'men': [
                    'men', 'male', 'prostate', 'testosterone', 'erectile',
                    'masculine', 'paternal'
                ],
                'children': [
                    'children', 'pediatric', 'kids', 'infant', 'baby',
                    'toddler', 'adolescent', 'teenager'
                ],
                'elderly': [
                    'elderly', 'senior', 'aging', 'geriatric', 'old age',
                    'retirement'
                ],
                'athletes': [
                    'athlete', 'sports', 'performance', 'training',
                    'competition', 'athletic'
                ]
            },
            
            'fitness': {
                'exercise': [
                    'exercise', 'workout', 'training', 'physical activity',
                    'cardio', 'strength', 'aerobic'
                ],
                'sports': [
                    'sports', 'athletic', 'competition', 'performance',
                    'running', 'swimming', 'cycling'
                ],
                'yoga_mindfulness': [
                    'yoga', 'pilates', 'meditation', 'mindfulness', 'tai chi'
                ]
            },
            
            'lifestyle': {
                'wellness': [
                    'wellness', 'wellbeing', 'healthy living', 'self care',
                    'balance', 'harmony'
                ],
                'prevention': [
                    'prevention', 'preventive', 'screening', 'early detection',
                    'immunization', 'vaccination'
                ],
                'sleep_health': [
                    'sleep', 'insomnia', 'sleep quality', 'circadian',
                    'rest', 'sleep disorder'
                ],
                'mental_wellness': [
                    'stress management', 'mindfulness', 'meditation',
                    'relaxation', 'mental health'
                ]
            }
        }
    
    def _build_tag_standardization(self) -> Dict:
        """Build tag standardization rules"""
        return {
            # Standardize common variations
            'diabetes_research': ['diabetes research', 'diabetic research'],
            'nutrition_research': ['nutrition research', 'nutritional research'],
            'medical_research': ['medical research', 'health research', 'clinical research'],
            'obesity_research': ['obesity research', 'weight research'],
            'heart_health': ['heart health', 'cardiac health', 'cardiovascular health'],
            'gut_health': ['gut health', 'digestive health', 'intestinal health'],
            'women_health': ['women health', 'women\'s health', 'female health'],
            'men_health': ['men health', 'men\'s health', 'male health'],
            'mental_health': ['mental health', 'psychological health', 'psychiatric health'],
            'preventive_care': ['preventive care', 'prevention', 'preventative care'],
            'weight_management': ['weight management', 'weight control', 'weight loss'],
            'hormone_health': ['hormone health', 'hormonal health', 'endocrine health']
        }
    
    def categorize_article(self, title: str, summary: str, existing_category: str = None) -> Tuple[str, str, List[str]]:
        """
        Categorize an article and return (category, subcategory, standardized_tags)
        """
        text = f"{title} {summary}".lower()
        
        # Calculate scores for each category
        category_scores = {}
        for category, rules in self.category_rules.items():
            score = 0
            
            # Keyword matching
            for keyword in rules['keywords']:
                if keyword.lower() in text:
                    # Title matches get higher weight
                    title_matches = title.lower().count(keyword.lower()) * 3
                    summary_matches = summary.lower().count(keyword.lower()) * 1
                    score += (title_matches + summary_matches) * rules['weight_multiplier']
            
            # Pattern matching for titles
            if 'title_patterns' in rules:
                for pattern in rules['title_patterns']:
                    if re.search(pattern, title.lower()):
                        score += 5 * rules['weight_multiplier']
            
            # Apply exclusions
            if 'exclude_patterns' in rules:
                for exclude_pattern in rules['exclude_patterns']:
                    if re.search(exclude_pattern, text):
                        score *= 0.5  # Reduce score by 50%
            
            if score > 0:
                category_scores[category] = score
        
        # Determine best category
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            best_category = existing_category or 'news'
        
        # Determine subcategory
        subcategory = self._determine_subcategory(best_category, text)
        
        # Generate standardized tags
        tags = self._generate_tags(best_category, subcategory, title, summary)
        
        return best_category, subcategory, tags
    
    def _determine_subcategory(self, category: str, text: str) -> str:
        """Determine the best subcategory for a given category"""
        if category not in self.subcategory_rules:
            return 'general'
        
        subcategory_scores = {}
        for subcategory, keywords in self.subcategory_rules[category].items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    score += text.count(keyword.lower())
            
            if score > 0:
                subcategory_scores[subcategory] = score
        
        if subcategory_scores:
            return max(subcategory_scores.items(), key=lambda x: x[1])[0]
        else:
            return 'general'
    
    def _generate_tags(self, category: str, subcategory: str, title: str, summary: str) -> List[str]:
        """Generate standardized tags for an article"""
        text = f"{title} {summary}".lower()
        tags = set()
        
        # Add category-based tags
        if category == 'diseases':
            if 'diabetes' in text:
                tags.update(['diabetes', 'blood sugar', 'insulin'])
            if 'heart' in text or 'cardiac' in text:
                tags.update(['heart health', 'cardiovascular'])
            if 'obesity' in text or 'weight' in text:
                tags.update(['obesity', 'weight management'])
            if 'research' in text or 'study' in text:
                tags.add('medical research')
        
        elif category == 'nutrition':
            if 'vitamin' in text or 'supplement' in text:
                tags.update(['micronutrients', 'nutrition'])
            if 'diet' in text:
                tags.add('nutrition')
            if 'research' in text or 'study' in text:
                tags.add('nutrition research')
            if 'gut' in text:
                tags.add('gut health')
        
        elif category == 'audience':
            if 'women' in text or 'female' in text:
                tags.add('women health')
            if 'men' in text or 'male' in text:
                tags.add('men health')
            if 'children' in text or 'pediatric' in text:
                tags.add('children')
            if 'elderly' in text or 'senior' in text:
                tags.add('elderly')
        
        elif category == 'news':
            if 'policy' in text or 'government' in text:
                tags.add('policy and regulation')
            if 'international' in text or 'global' in text:
                tags.add('international')
            if 'breaking' in text or 'urgent' in text:
                tags.add('latest')
        
        # Add subcategory as tag if it's meaningful
        if subcategory != 'general':
            tags.add(subcategory.replace('_', ' '))
        
        # Standardize tags
        standardized_tags = []
        for tag in tags:
            standardized = self._standardize_tag(tag)
            standardized_tags.append(standardized)
        
        return list(set(standardized_tags))  # Remove duplicates
    
    def _standardize_tag(self, tag: str) -> str:
        """Standardize a tag using the standardization rules"""
        tag_lower = tag.lower()
        
        for standard_tag, variations in self.tag_standardization.items():
            if tag_lower in [v.lower() for v in variations]:
                return standard_tag.replace('_', ' ')
        
        return tag
    
    def update_database_categorization(self) -> int:
        """Update all articles in the database with improved categorization"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all articles
            cursor.execute("SELECT id, title, summary, categories, tags FROM articles")
            articles = cursor.fetchall()
            
            updated_count = 0
            
            for article in articles:
                article_id, title, summary, current_category, current_tags = article
                
                if not title:
                    continue
                
                # Skip if summary is None
                if summary is None:
                    summary = ""
                
                # Categorize the article
                new_category, new_subcategory, new_tags = self.categorize_article(
                    title, summary, current_category
                )
                
                # Update the article
                new_tags_json = json.dumps(new_tags)
                
                cursor.execute("""
                    UPDATE articles 
                    SET categories = ?, subcategory = ?, tags = ?
                    WHERE id = ?
                """, (new_category, new_subcategory, new_tags_json, article_id))
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    logger.info(f"Updated {updated_count} articles...")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully updated {updated_count} articles")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating database categorization: {e}")
            return 0

def main():
    """Main function to run the improved categorization"""
    db_path = Path(__file__).parent.parent / "data" / "articles.db"
    
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return
    
    logger.info("Starting improved categorization process...")
    categorizer = ImprovedArticleCategorizer(str(db_path))
    
    # Update the database
    updated_count = categorizer.update_database_categorization()
    
    logger.info(f"Categorization complete! Updated {updated_count} articles")

if __name__ == "__main__":
    main()
