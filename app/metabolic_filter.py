"""
Metabolic Health Filter
Filters articles to ensure they are relevant to metabolic health topics
before categorization and before sending to frontend.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from difflib import SequenceMatcher

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetabolicHealthFilter:
    """
    Filter articles to ensure they contain metabolic health-related content
    """
    
    def __init__(self):
        self.metabolic_keywords = self._build_metabolic_keywords()
        self.semantic_patterns = self._build_semantic_patterns()
        
    def _build_metabolic_keywords(self) -> Dict[str, List[str]]:
        """Build comprehensive metabolic health keywords and their semantic variations"""
        return {
            "metabolic_diseases": [
                "metabolic diseases", "metabolic syndrome", "obesity", "type 2 diabetes", 
                "insulin resistance", "hypertension", "hyperlipidemia", 
                "non-alcoholic fatty liver disease", "nafld", "cardiometabolic disorders", 
                "mitochondrial dysfunction", "endocrine disruption", "diabetic", "diabetes",
                "blood sugar", "glucose metabolism", "lipid disorders", "fatty liver",
                "metabolic disorder", "syndrome x", "insulin sensitivity", "glucose intolerance"
            ],
            
            "metabolism_general": [
                "basal metabolic rate", "bmr", "energy homeostasis", "anabolism", 
                "catabolism", "glucose metabolism", "lipid metabolism", "protein metabolism", 
                "nutrient absorption", "hormonal regulation", "gut microbiota", "metabolism",
                "metabolic rate", "energy expenditure", "caloric metabolism", "nutrient metabolism",
                "cellular metabolism", "enzymatic processes", "biochemical pathways",
                "energy production", "metabolic pathways"
            ],
            
            "food_nutrition": [
                "macronutrients", "micronutrients", "nutrient deficiency", "overnutrition", 
                "dietary patterns", "processed foods", "ultra-processed foods", "caloric intake", 
                "glycemic index", "dietary fiber", "antioxidants", "probiotics", "prebiotics",
                "nutrition", "diet", "food", "eating", "meal", "supplement", "vitamin", "mineral",
                "healthy eating", "balanced diet", "nutrients", "nutritional value", "food quality"
            ],
            
            "agriculture": [
                "agrochemicals", "pesticide residues", "gmos", "genetically modified organisms", 
                "monoculture", "soil degradation", "crop diversity", "food security", 
                "agroecology", "organic farming", "livestock emissions", "agro-industrial processing",
                "agricultural practices", "farming methods", "food production", "pesticides",
                "herbicides", "chemical fertilizers", "sustainable agriculture"
            ],
            
            "sugar_sweeteners": [
                "added sugars", "high-fructose corn syrup", "refined carbohydrates", 
                "artificial sweeteners", "sugar-sweetened beverages", "insulin spike", 
                "fructose metabolism", "glycemic load", "sugar addiction", "hidden sugars",
                "sugar", "sweeteners", "fructose", "sucrose", "glucose", "corn syrup",
                "simple carbohydrates", "refined sugar", "natural sugars"
            ],
            
            "air_pollution": [
                "particulate matter", "pm2.5", "oxidative stress", "inflammation", 
                "endocrine-disrupting chemicals", "edcs", "metabolic dysregulation", 
                "respiratory-metabolic link", "urban smog", "toxic air exposure",
                "air pollution", "environmental toxins", "air quality", "pollutants",
                "atmospheric pollution", "environmental health"
            ],
            
            "water_pollution": [
                "heavy metals", "lead", "mercury", "nitrate contamination", "microplastics", 
                "pesticide runoff", "endocrine disruptors", "toxic algal blooms", 
                "drinking water safety", "bioaccumulation", "industrial effluents",
                "water pollution", "water contamination", "water quality", "toxic metals",
                "chemical pollutants", "water safety"
            ]
        }
    
    def _build_semantic_patterns(self) -> List[str]:
        """Build regex patterns for semantic matching"""
        return [
            r'\b(metabol|diabet|insulin|glucose|obesit|weight|nutrition|diet)\w*\b',
            r'\b(cardiovascular|heart|blood pressure|cholesterol)\w*\b',
            r'\b(hormone|endocrin|thyroid|adrenal)\w*\b',
            r'\b(food|eat|meal|calor|nutrient)\w*\b',
            r'\b(exercise|fitness|physical activity|lifestyle)\w*\b',
            r'\b(gut|microbiom|digestiv|intestin)\w*\b',
            r'\b(inflammation|oxidativ|stress|toxic)\w*\b',
            r'\b(liver|hepatic|fatty liver|nafld)\w*\b',
            r'\b(sugar|sweet|fructos|glycem)\w*\b',
            r'\b(pollut|contamin|pesticid|chemical)\w*\b'
        ]
    
    def contains_metabolic_content(self, title: str, summary: str, content: str = "") -> Tuple[bool, float, List[str]]:
        """
        Check if article contains metabolic health-related content
        
        Returns:
            Tuple of (is_relevant, relevance_score, matched_keywords)
        """
        # Combine all text for analysis
        full_text = f"{title} {summary} {content}".lower()
        
        matched_keywords = []
        total_score = 0.0
        
        # Check exact keyword matches
        for category, keywords in self.metabolic_keywords.items():
            for keyword in keywords:
                if keyword.lower() in full_text:
                    matched_keywords.append(keyword)
                    # Weight based on where the match occurs
                    if keyword.lower() in title.lower():
                        total_score += 3.0  # Title matches are most important
                    elif keyword.lower() in summary.lower():
                        total_score += 2.0  # Summary matches are important
                    else:
                        total_score += 1.0  # Content matches have lower weight
        
        # Check semantic patterns
        for pattern in self.semantic_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                if match not in [kw.lower() for kw in matched_keywords]:
                    matched_keywords.append(match)
                    total_score += 0.5  # Lower weight for pattern matches
        
        # Calculate relevance score (normalized)
        max_possible_score = len(full_text.split()) * 0.1  # Reasonable max based on text length
        relevance_score = min(total_score / max(max_possible_score, 1.0), 1.0)
        
        # Determine if relevant (require minimum score and at least one strong keyword match)
        is_relevant = (
            relevance_score >= 0.1 and  # Minimum relevance threshold
            len(matched_keywords) >= 1 and  # At least one keyword match
            total_score >= 1.0  # At least one significant match
        )
        
        if is_relevant:
            logger.debug(f"Article relevant - Score: {relevance_score:.2f}, Keywords: {matched_keywords[:5]}")
        
        return is_relevant, relevance_score, matched_keywords
    
    def filter_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Filter a list of articles to only include metabolic health-related content
        """
        filtered_articles = []
        
        for article in articles:
            title = article.get('title', '')
            summary = article.get('summary', '')
            content = article.get('content', '')
            
            is_relevant, score, keywords = self.contains_metabolic_content(title, summary, content)
            
            if is_relevant:
                # Add metadata about the filtering
                article['metabolic_relevance_score'] = score
                article['metabolic_keywords'] = keywords[:10]  # Top 10 keywords
                filtered_articles.append(article)
            else:
                logger.debug(f"Filtered out non-metabolic article: {title[:50]}")
        
        logger.info(f"Filtered {len(articles)} articles down to {len(filtered_articles)} metabolic health articles")
        return filtered_articles
    
    def enhance_categorization(self, article: Dict) -> Dict:
        """
        Enhance article categorization based on metabolic health focus
        """
        title = article.get('title', '')
        summary = article.get('summary', '')
        current_category = article.get('category', '')
        current_tags = article.get('tags', [])
        
        # Ensure tags is a list
        if isinstance(current_tags, str):
            try:
                import json
                current_tags = json.loads(current_tags)
            except:
                current_tags = [tag.strip() for tag in current_tags.split(',') if tag.strip()]
        
        if not isinstance(current_tags, list):
            current_tags = []
        
        # Check for specific metabolic conditions and enhance categorization
        text = f"{title} {summary}".lower()
        
        # Add metabolic-specific tags
        metabolic_tags = set(current_tags)
        
        # Disease-specific enhancements
        if any(word in text for word in ['diabetes', 'diabetic', 'blood sugar', 'insulin']):
            metabolic_tags.update(['diabetes', 'blood sugar', 'insulin', 'metabolic disease'])
            if current_category not in ['diseases', 'metabolic']:
                article['category'] = 'diseases'
                article['subcategory'] = 'diabetes'
        
        if any(word in text for word in ['obesity', 'weight loss', 'overweight', 'bmi']):
            metabolic_tags.update(['obesity', 'weight management', 'metabolic syndrome'])
            if current_category not in ['diseases', 'metabolic']:
                article['category'] = 'diseases'
                article['subcategory'] = 'obesity'
        
        if any(word in text for word in ['metabolic syndrome', 'insulin resistance', 'syndrome x']):
            metabolic_tags.update(['metabolic syndrome', 'insulin resistance', 'cardiometabolic'])
            if current_category not in ['diseases', 'metabolic']:
                article['category'] = 'diseases'
                article['subcategory'] = 'metabolic'
        
        # Nutrition-specific enhancements
        if any(word in text for word in ['diet', 'nutrition', 'food', 'eating', 'meal']):
            metabolic_tags.update(['nutrition', 'diet', 'healthy eating'])
            if current_category == '' or current_category == 'news':
                article['category'] = 'nutrition'
                article['subcategory'] = 'general'
        
        # Pollution/environmental enhancements
        if any(word in text for word in ['pollution', 'pesticide', 'chemical', 'toxic', 'environmental']):
            metabolic_tags.update(['environmental health', 'pollution', 'toxins'])
            if current_category == '' or current_category == 'news':
                article['category'] = 'environmental'
                article['subcategory'] = 'pollution'
        
        # Update tags
        article['tags'] = list(metabolic_tags)
        
        return article


class ArticleDeduplicator:
    """
    Remove duplicate articles before sending to frontend
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        # Remove extra spaces, punctuation, and convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    def are_duplicates(self, article1: Dict, article2: Dict) -> bool:
        """Check if two articles are duplicates"""
        title1 = self.normalize_title(article1.get('title', ''))
        title2 = self.normalize_title(article2.get('title', ''))
        
        # Check title similarity
        title_similarity = self.calculate_similarity(title1, title2)
        
        if title_similarity >= self.similarity_threshold:
            return True
        
        # Check URL similarity (exact match)
        url1 = article1.get('url', '')
        url2 = article2.get('url', '')
        if url1 and url2 and url1 == url2:
            return True
        
        # Check content similarity if available
        summary1 = article1.get('summary', '')
        summary2 = article2.get('summary', '')
        
        if summary1 and summary2:
            summary_similarity = self.calculate_similarity(summary1, summary2)
            if summary_similarity >= 0.9:  # Higher threshold for summary
                return True
        
        return False
    
    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles from the list"""
        if not articles:
            return articles
        
        deduplicated = []
        seen_titles = set()
        seen_urls = set()
        
        for article in articles:
            title = self.normalize_title(article.get('title', ''))
            url = article.get('url', '')
            
            # Quick check for exact matches
            if title in seen_titles or (url and url in seen_urls):
                logger.debug(f"Removing duplicate article: {article.get('title', '')[:50]}")
                continue
            
            # Check for similar articles
            is_duplicate = False
            for existing_article in deduplicated:
                if self.are_duplicates(article, existing_article):
                    logger.debug(f"Removing similar article: {article.get('title', '')[:50]}")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(article)
                seen_titles.add(title)
                if url:
                    seen_urls.add(url)
        
        logger.info(f"Deduplicated {len(articles)} articles down to {len(deduplicated)} unique articles")
        return deduplicated


# Global instances
metabolic_filter = MetabolicHealthFilter()
article_deduplicator = ArticleDeduplicator()

def filter_and_deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """
    Main function to filter for metabolic health content and remove duplicates
    """
    if not articles:
        return articles
    
    logger.info(f"Starting filter and deduplication process for {len(articles)} articles")
    
    # Step 1: Filter for metabolic health content
    metabolic_articles = metabolic_filter.filter_articles(articles)
    
    # Step 2: Enhance categorization for metabolic focus
    enhanced_articles = []
    for article in metabolic_articles:
        enhanced_article = metabolic_filter.enhance_categorization(article)
        enhanced_articles.append(enhanced_article)
    
    # Step 3: Remove duplicates
    final_articles = article_deduplicator.deduplicate_articles(enhanced_articles)
    
    logger.info(f"Final result: {len(final_articles)} unique metabolic health articles")
    return final_articles
