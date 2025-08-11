"""
Health Article Categorizer
Intelligent categorization system that maps articles to frontend menu structure.
"""

import re
import logging
from typing import Tuple, List, Dict, Optional
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class HealthCategorizer:
    """
    Intelligent health article categorizer that maps content to frontend menu structure.
    
    Frontend Menu Structure:
    - news: ['latest', 'policy and regulation', 'govt schemes', 'international']
    - diseases: ['diabetes', 'obesity', 'inflammation', 'cardiovascular', 'liver', 'kidney', 'thyroid', 'metabolic', 'sleep disorders', 'skin', 'eyes and ears', 'reproductive health']
    - solutions: ['nutrition', 'fitness', 'lifestyle', 'wellness', 'prevention']
    - food: ['natural food', 'organic food', 'processed food', 'fish and seafood', 'food safety']
    - audience: ['women', 'men', 'children', 'teenagers', 'seniors', 'athletes', 'families']
    - trending: ['gut health', 'mental health', 'hormones', 'addiction', 'sleep health', 'sexual wellness']
    - blogs_and_opinions: []
    """
    
    def __init__(self):
        self.category_keywords = self._load_category_keywords()
        self.frontend_mappings = self._get_frontend_mappings()
        
    def _load_category_keywords(self) -> Dict:
        """Load category keywords from YAML file"""
        try:
            yaml_path = Path(__file__).parent / "health_categories.yml"
            if yaml_path.exists():
                with open(yaml_path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file) or {}
        except Exception as e:
            logger.warning(f"Could not load category keywords: {e}")
        
        return {}
    
    def _get_frontend_mappings(self) -> Dict[str, Dict[str, List[str]]]:
        """Define mapping from frontend tags to keywords and patterns"""
        return {
            # NEWS CATEGORY
            'news': {
                'latest': [
                    'breaking', 'recent', 'new study', 'latest research', 'update',
                    'announced', 'report', 'findings', 'discovers', 'reveals',
                    'breakthrough', 'development', 'alert', 'warning', 'today'
                ],
                'policy and regulation': [
                    'health policy', 'healthcare policy', 'medical policy', 'public health policy',
                    'government health', 'health regulation', 'medical regulation', 'healthcare regulation',
                    'health law', 'medical law', 'healthcare law', 'policy', 'regulation',
                    'fda approval', 'drug approval', 'medical approval', 'clinical guidelines',
                    'health standards', 'medical standards', 'healthcare standards',
                    'health ministry', 'health department', 'public health department',
                    'government scheme', 'medical establishment', 'hospital registration',
                    'health surveillance', 'vaccination policy', 'immunization policy'
                ],
                'govt schemes': [
                    'government scheme', 'govt scheme', 'ayushman bharat', 'pradhan mantri',
                    'cghs', 'health scheme', 'public health scheme', 'national health',
                    'health insurance', 'jan arogya', 'health card', 'beneficiary',
                    'government health program', 'state health scheme'
                ],
                'international': [
                    'international', 'global', 'world health', 'who', 'global health',
                    'pandemic', 'epidemic', 'united nations', 'unicef', 'worldwide',
                    'cross-border', 'global study', 'international research'
                ]
            },
            
            # DISEASES CATEGORY
            'diseases': {
                'diabetes': [
                    'diabetes', 'diabetic', 'blood sugar', 'glucose', 'insulin',
                    'type 1 diabetes', 'type 2 diabetes', 'gestational diabetes',
                    'hyperglycemia', 'hypoglycemia', 'prediabetes', 'glycemic'
                ],
                'obesity': [
                    'obesity', 'overweight', 'weight', 'bmi', 'body mass index',
                    'weight management', 'adipose', 'fat', 'bariatric', 'weight loss'
                ],
                'inflammation': [
                    'inflammation', 'inflammatory', 'immune', 'cytokine', 'autoimmune',
                    'arthritis', 'rheumatoid', 'lupus', 'inflammatory bowel', 'crohn'
                ],
                'cardiovascular': [
                    'cardiovascular', 'heart', 'cardiac', 'heart disease', 'blood pressure',
                    'hypertension', 'cholesterol', 'coronary', 'artery', 'stroke',
                    'heart attack', 'angina', 'atrial fibrillation'
                ],
                'liver': [
                    'liver', 'hepatic', 'fatty liver', 'nafld', 'liver function',
                    'hepatitis', 'cirrhosis', 'liver disease', 'liver enzymes'
                ],
                'kidney': [
                    'kidney', 'renal', 'dialysis', 'kidney disease', 'nephrology',
                    'chronic kidney', 'kidney failure', 'glomerular'
                ],
                'thyroid': [
                    'thyroid', 'hypothyroid', 'hyperthyroid', 'thyroid gland',
                    'thyroid hormone', 'tsh', 'thyroxine', 'goiter', 'thyroiditis'
                ],
                'metabolic': [
                    'metabolic', 'metabolism', 'metabolic syndrome', 'energy',
                    'biochemical', 'metabolic disorder', 'endocrine', 'hormone'
                ],
                'sleep disorders': [
                    'sleep disorder', 'insomnia', 'sleep apnea', 'narcolepsy',
                    'restless leg', 'circadian rhythm', 'sleep quality', 'sleep study'
                ],
                'skin': [
                    'skin', 'dermatology', 'dermatitis', 'acne', 'eczema',
                    'psoriasis', 'melanoma', 'skin cancer', 'rash', 'dermatologist'
                ],
                'eyes and ears': [
                    'eyes', 'vision', 'hearing', 'ear', 'ophthalmology', 'optical',
                    'auditory', 'glaucoma', 'cataract', 'retina', 'tinnitus', 'deaf'
                ],
                'reproductive health': [
                    'reproductive', 'fertility', 'pregnancy', 'maternal', 'gynecology',
                    'obstetrics', 'contraception', 'menstrual', 'ovarian', 'uterine'
                ]
            },
            
            # SOLUTIONS CATEGORY
            'solutions': {
                'nutrition': [
                    'nutrition', 'diet', 'food', 'nutritional', 'dietary', 'nutrient',
                    'vitamin', 'mineral', 'supplement', 'eating', 'meal', 'calorie'
                ],
                'fitness': [
                    'fitness', 'exercise', 'workout', 'training', 'physical activity',
                    'gym', 'sports', 'running', 'cycling', 'swimming', 'strength'
                ],
                'lifestyle': [
                    'lifestyle', 'life style', 'health habits', 'daily routine',
                    'behavior', 'habit', 'routine', 'lifestyle change'
                ],
                'wellness': [
                    'wellness', 'wellbeing', 'health', 'self care', 'mindfulness',
                    'meditation', 'stress management', 'work life balance'
                ],
                'prevention': [
                    'prevention', 'preventive', 'screening', 'early detection',
                    'preventive care', 'immunization', 'vaccination', 'checkup'
                ]
            },
            
            # FOOD CATEGORY
            'food': {
                'natural food': [
                    'natural food', 'whole food', 'unprocessed', 'farm fresh',
                    'natural', 'raw food', 'fresh produce', 'farm to table'
                ],
                'organic food': [
                    'organic', 'organic food', 'pesticide free', 'chemical free',
                    'organic farming', 'certified organic', 'organic produce'
                ],
                'processed food': [
                    'processed food', 'ultra processed', 'packaged food', 'artificial',
                    'preservatives', 'additives', 'fast food', 'junk food'
                ],
                'fish and seafood': [
                    'fish', 'seafood', 'omega', 'marine', 'salmon', 'tuna',
                    'shellfish', 'seafood safety', 'fish oil', 'aquaculture'
                ],
                'food safety': [
                    'food safety', 'foodborne', 'contamination', 'food hygiene',
                    'food poisoning', 'salmonella', 'e coli', 'food recall'
                ]
            },
            
            # AUDIENCE CATEGORY
            'audience': {
                'women': [
                    'women', 'female', 'woman', 'maternal', 'pregnancy',
                    'menopause', 'gynecology', 'breast', 'cervical', 'ovarian'
                ],
                'men': [
                    'men', 'male', 'man', 'prostate', 'testosterone',
                    'masculine', 'paternal', 'erectile', 'sperm'
                ],
                'children': [
                    'children', 'pediatric', 'kids', 'child', 'infant',
                    'toddler', 'preschool', 'childhood', 'baby'
                ],
                'teenagers': [
                    'teenager', 'adolescent', 'teen', 'young adult', 'puberty',
                    'teenage', 'adolescence', 'high school'
                ],
                'seniors': [
                    'senior', 'elderly', 'geriatric', 'aging', 'old age',
                    'retirement', 'aged', 'older adult'
                ],
                'athletes': [
                    'athlete', 'sports', 'performance', 'training', 'competition',
                    'athletic', 'professional sports', 'olympic'
                ],
                'families': [
                    'family', 'household', 'parent', 'parenting', 'family health',
                    'household health', 'family planning'
                ]
            },
            
            # TRENDING CATEGORY
            'trending': {
                'gut health': [
                    'gut health', 'microbiome', 'digestive', 'intestinal', 'probiotic',
                    'gut bacteria', 'digestive health', 'gut microbiota'
                ],
                'mental health': [
                    'mental health', 'depression', 'anxiety', 'stress', 'psychology',
                    'psychiatric', 'bipolar', 'ptsd', 'therapy', 'counseling'
                ],
                'hormones': [
                    'hormone', 'hormonal', 'endocrine', 'insulin', 'cortisol',
                    'estrogen', 'testosterone', 'growth hormone', 'adrenaline'
                ],
                'addiction': [
                    'addiction', 'substance abuse', 'dependency', 'alcoholism',
                    'drug abuse', 'smoking', 'nicotine', 'gambling addiction'
                ],
                'sleep health': [
                    'sleep health', 'sleep', 'insomnia', 'sleep quality',
                    'circadian rhythm', 'sleep hygiene', 'sleep pattern'
                ],
                'sexual wellness': [
                    'sexual wellness', 'sexual health', 'sexuality', 'libido',
                    'intimate health', 'sexual dysfunction', 'reproductive wellness'
                ]
            }
        }
    
    def categorize_article(self, title: str, summary: str, source_category: Optional[str] = None) -> Tuple[str, str]:
        """
        Categorize an article based on title, summary, and source category.
        
        Args:
            title: Article title
            summary: Article summary/description
            source_category: Source category hint (optional)
        
        Returns:
            Tuple of (main_category, subcategory)
        """
        
        title = title.lower() if title else ""
        summary = summary.lower() if summary else ""
        content = f"{title} {summary}"
        
        # Track the best matches
        best_matches = []
        
        # Score each category and subcategory
        for main_category, subcategories in self.frontend_mappings.items():
            for subcategory, keywords in subcategories.items():
                score = self._calculate_match_score(content, keywords)
                if score > 0:
                    best_matches.append((score, main_category, subcategory))
        
        # Sort by score (highest first)
        best_matches.sort(reverse=True, key=lambda x: x[0])
        
        if best_matches:
            score, main_category, subcategory = best_matches[0]
            
            # Special logic for news articles
            if main_category == 'news':
                # Check if it's a policy/regulation article
                if self._is_policy_article(content):
                    return 'news', 'policy_and_regulation'
                # Check if it's a government scheme
                elif self._is_govt_scheme_article(content):
                    return 'news', 'govt_schemes'
                # Check if it's international
                elif self._is_international_article(content):
                    return 'news', 'international'
                # Otherwise it's latest news
                else:
                    return 'news', 'latest'
            
            # Convert subcategory name to database format
            db_subcategory = subcategory.replace(' ', '_').replace('and', 'and')
            return main_category, db_subcategory
        
        # Fallback categorization
        return self._fallback_categorization(content, source_category)
    
    def _calculate_match_score(self, content: str, keywords: List[str]) -> float:
        """Calculate how well content matches the given keywords"""
        score = 0.0
        content_words = content.split()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Exact phrase match (higher weight)
            if keyword_lower in content:
                score += 3.0
            
            # Individual word matches
            keyword_words = keyword_lower.split()
            matches = sum(1 for word in keyword_words if word in content_words)
            if matches > 0:
                score += (matches / len(keyword_words)) * 1.5
        
        return score
    
    def _is_policy_article(self, content: str) -> bool:
        """Check if article is about policy/regulation"""
        policy_indicators = [
            'health policy', 'medical policy', 'healthcare policy', 'government health',
            'health regulation', 'fda approval', 'health ministry', 'health department',
            'government scheme', 'public health policy', 'health law', 'medical law'
        ]
        
        return any(indicator in content for indicator in policy_indicators)
    
    def _is_govt_scheme_article(self, content: str) -> bool:
        """Check if article is about government schemes"""
        scheme_indicators = [
            'ayushman bharat', 'pradhan mantri', 'cghs', 'jan arogya',
            'government scheme', 'health scheme', 'health card'
        ]
        
        return any(indicator in content for indicator in scheme_indicators)
    
    def _is_international_article(self, content: str) -> bool:
        """Check if article is international/global"""
        international_indicators = [
            'international', 'global', 'world health', 'who', 'pandemic',
            'worldwide', 'united nations', 'unicef', 'global study'
        ]
        
        return any(indicator in content for indicator in international_indicators)
    
    def _fallback_categorization(self, content: str, source_category: Optional[str]) -> Tuple[str, str]:
        """Fallback categorization when no clear match is found"""
        
        # Use source category if available
        if source_category:
            source_mappings = {
                'medical_research': ('diseases', 'general'),
                'health_news': ('news', 'latest'),
                'public_health': ('news', 'policy_and_regulation'),
                'nutrition_science': ('solutions', 'nutrition'),
                'environmental_health': ('news', 'international'),
                'global_health': ('news', 'international')
            }
            
            if source_category in source_mappings:
                return source_mappings[source_category]
        
        # Basic keyword fallback
        if any(word in content for word in ['study', 'research', 'trial']):
            return 'diseases', 'general'
        elif any(word in content for word in ['policy', 'government', 'regulation']):
            return 'news', 'policy_and_regulation'
        elif any(word in content for word in ['international', 'global', 'world']):
            return 'news', 'international'
        
        # Default fallback
        return 'news', 'latest'

# Create global instance
health_categorizer = HealthCategorizer()
