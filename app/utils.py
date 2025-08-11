"""
Metabolical Backend Utilities - Simplified and Clean
Database operations and utility functions for the health articles API.
"""

import sqlite3
import json
import threading
import re
import html

import os
import sys
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from contextlib import contextmanager
import logging
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import metabolic filter and config
try:
    from .metabolic_filter import filter_and_deduplicate_articles, metabolic_filter
    from .config import config
    logger.info("✅ Successfully imported metabolic_filter and config")
except ImportError:
    try:
        import sys
        sys.path.append(str(Path(__file__).parent))
        from metabolic_filter import filter_and_deduplicate_articles, metabolic_filter
        from config import config
        logger.info("✅ Successfully imported metabolic_filter and config (fallback)")
    except ImportError as e:
        logger.warning(f"Could not import metabolic_filter: {e}")
        # Create fallback functions
        def filter_and_deduplicate_articles(articles):
            return articles
        def metabolic_filter(article):
            return True, 1.0
        
        class FallbackConfig:
            ENABLE_METABOLIC_FILTER = False
            ENABLE_DEDUPLICATION = False  # Disable to avoid further import issues
            
            @classmethod
            def is_metabolic_filter_enabled(cls):
                return False
            
            @classmethod 
            def is_deduplication_enabled(cls):
                return False
        config = FallbackConfig()
        logger.info("Using fallback metabolic filter configuration")



# Database path - robust configuration for both local and container environments
def get_database_path():
    """Get the database path with proper fallbacks for different environments"""
    
    # Check for environment variable override first
    env_db_path = os.getenv('DATABASE_PATH')
    if env_db_path:
        env_path = Path(env_db_path)
        if env_path.exists() or env_path.parent.exists():
            logger.info(f"📂 Using environment database path: {env_path}")
            env_path.parent.mkdir(parents=True, exist_ok=True)
            return str(env_path)
    
    # First try: data directory (new structure)
    data_path = Path(__file__).parent.parent / "data" / "articles.db"
    
    # Second try: legacy db directory
    legacy_path = Path(__file__).parent.parent / "db" / "articles.db"
    
    # Third try: current directory (for container environments)
    current_dir_path = Path("data") / "articles.db"
    
    # Fourth try: absolute container path
    container_path = Path("/app/data/articles.db")
    
    paths_to_try = [data_path, legacy_path, current_dir_path, container_path]
    
    for path in paths_to_try:
        if path.exists():
            logger.info(f"📂 Database found at: {path}")
            return str(path)
    
    # If no database exists, create one in the most appropriate location
    # Prefer data directory structure
    if data_path.parent.exists() or data_path.parent.is_dir():
        # data directory exists, use it
        data_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Creating new database at: {data_path}")
        return str(data_path)
    elif current_dir_path.parent.exists() or Path("data").exists():
        # Current directory data folder exists
        current_dir_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Creating new database at: {current_dir_path}")
        return str(current_dir_path)
    elif container_path.parent.exists():
        # Container environment
        container_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Creating new database at: {container_path}")
        return str(container_path)
    else:
        # Last resort: use data_path and create directories
        data_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Creating new database with directories at: {data_path}")
        return str(data_path)

DB_PATH = get_database_path()

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
    ],
    
    # METABOLIC DISEASES CATEGORY
    "metabolic diseases": [
        "metabolic diseases", "metabolic syndrome", "metabolic disorder",
        "cardiometabolic", "endocrine disorder", "metabolic dysfunction"
    ],
    "metabolic syndrome": [
        "metabolic syndrome", "syndrome x", "insulin resistance syndrome",
        "cardiometabolic syndrome", "multiple metabolic risk factors"
    ],
    "obesity": [
        "obesity", "obese", "overweight", "weight loss", "weight gain",
        "BMI", "body mass index", "adipose", "fat", "bariatric",
        "metabolic syndrome", "weight management", "calorie", "portion",
        "abdominal obesity", "visceral fat", "adiposity"
    ],
    "type 2 diabetes": [
        "type 2 diabetes", "diabetes mellitus", "adult-onset diabetes",
        "non-insulin dependent diabetes", "t2dm", "diabetic", "hyperglycemia"
    ],
    "insulin resistance": [
        "insulin resistance", "insulin sensitivity", "glucose intolerance",
        "prediabetes", "impaired glucose tolerance", "insulin signaling"
    ],
    "hypertension": [
        "hypertension", "high blood pressure", "elevated blood pressure",
        "systolic pressure", "diastolic pressure", "prehypertension",
        "essential hypertension", "secondary hypertension"
    ],
    "hyperlipidemia": [
        "hyperlipidemia", "dyslipidemia", "high cholesterol", "elevated lipids",
        "triglycerides", "LDL cholesterol", "HDL cholesterol", "lipid profile"
    ],
    "nafld": [
        "NAFLD", "non-alcoholic fatty liver disease", "fatty liver",
        "hepatic steatosis", "liver fat", "NASH", "non-alcoholic steatohepatitis"
    ],
    "cardiometabolic disorders": [
        "cardiometabolic", "cardiovascular metabolic", "heart metabolism",
        "cardiac risk factors", "metabolic cardiovascular disease"
    ],
    "mitochondrial dysfunction": [
        "mitochondrial dysfunction", "mitochondria", "cellular energy",
        "oxidative phosphorylation", "ATP production", "mitochondrial health"
    ],
    "endocrine disruption": [
        "endocrine disruption", "endocrine disruptors", "hormonal disruption",
        "EDCs", "hormone interference", "endocrine system"
    ],
    
    # METABOLISM (GENERAL) CATEGORY
    "basal metabolic rate": [
        "basal metabolic rate", "BMR", "resting metabolic rate", "RMR",
        "metabolic rate", "energy expenditure", "caloric needs"
    ],
    "energy homeostasis": [
        "energy homeostasis", "energy balance", "caloric balance",
        "energy regulation", "metabolic balance", "energy metabolism"
    ],
    "anabolism": [
        "anabolism", "anabolic", "biosynthesis", "tissue building",
        "protein synthesis", "muscle building", "growth processes"
    ],
    "catabolism": [
        "catabolism", "catabolic", "breakdown", "metabolic breakdown",
        "energy release", "tissue breakdown", "degradation"
    ],
    "glucose metabolism": [
        "glucose metabolism", "blood sugar", "glycolysis", "gluconeogenesis",
        "glucose regulation", "carbohydrate metabolism", "glycemic control"
    ],
    "lipid metabolism": [
        "lipid metabolism", "fat metabolism", "lipolysis", "lipogenesis",
        "fatty acid oxidation", "cholesterol metabolism", "triglyceride metabolism"
    ],
    "protein metabolism": [
        "protein metabolism", "amino acid metabolism", "protein synthesis",
        "protein breakdown", "nitrogen balance", "amino acids"
    ],
    "nutrient absorption": [
        "nutrient absorption", "intestinal absorption", "bioavailability",
        "digestive absorption", "nutrient uptake", "malabsorption"
    ],
    "hormonal regulation": [
        "hormonal regulation", "endocrine regulation", "hormone control",
        "metabolic hormones", "insulin", "leptin", "ghrelin", "cortisol"
    ],
    "gut microbiota": [
        "gut microbiota", "microbiome", "intestinal bacteria", "gut bacteria",
        "digestive microbes", "probiotics", "gut health", "dysbiosis"
    ],
    
    # FOOD & NUTRITION CATEGORY (ENHANCED)
    "macronutrients": [
        "macronutrients", "carbohydrates", "proteins", "fats", "lipids",
        "macros", "energy nutrients", "caloric nutrients"
    ],
    "micronutrients": [
        "micronutrients", "vitamins", "minerals", "trace elements",
        "essential nutrients", "vitamin deficiency", "mineral deficiency"
    ],
    "nutrient deficiency": [
        "nutrient deficiency", "malnutrition", "vitamin deficiency",
        "mineral deficiency", "undernutrition", "nutritional gaps"
    ],
    "overnutrition": [
        "overnutrition", "excess nutrition", "caloric excess", "overeating",
        "nutritional excess", "overconsumption"
    ],
    "dietary patterns": [
        "dietary patterns", "eating patterns", "meal patterns", "diet quality",
        "nutritional patterns", "food habits", "eating behaviors"
    ],
    "processed foods": [
        "processed foods", "food processing", "packaged foods",
        "convenience foods", "industrial foods", "food manufacturing"
    ],
    "ultra-processed foods": [
        "ultra-processed foods", "UPFs", "highly processed", "industrial formulations",
        "food additives", "artificial ingredients", "processed food products"
    ],
    "caloric intake": [
        "caloric intake", "calorie consumption", "energy intake",
        "daily calories", "caloric density", "energy consumption"
    ],
    "glycemic index": [
        "glycemic index", "GI", "blood sugar response", "glucose response",
        "glycemic load", "carbohydrate ranking", "sugar impact"
    ],
    "dietary fiber": [
        "dietary fiber", "fiber", "roughage", "insoluble fiber", "soluble fiber",
        "prebiotic fiber", "resistant starch", "bulk"
    ],
    "antioxidants": [
        "antioxidants", "free radicals", "oxidative stress", "polyphenols",
        "flavonoids", "carotenoids", "vitamin C", "vitamin E"
    ],
    "probiotics prebiotics": [
        "probiotics", "prebiotics", "beneficial bacteria", "gut flora",
        "live cultures", "fermented foods", "digestive health"
    ],
    
    # AGRICULTURE CATEGORY
    "agrochemicals": [
        "agrochemicals", "agricultural chemicals", "farm chemicals",
        "crop chemicals", "agricultural inputs", "pesticides", "herbicides"
    ],
    "pesticide residues": [
        "pesticide residues", "chemical residues", "pesticide contamination",
        "food residues", "agricultural residues", "toxic residues"
    ],
    "gmos": [
        "GMOs", "genetically modified organisms", "genetic modification",
        "bioengineered foods", "transgenic crops", "genetic engineering"
    ],
    "monoculture": [
        "monoculture", "crop monoculture", "agricultural monoculture",
        "single crop farming", "biodiversity loss", "crop uniformity"
    ],
    "soil degradation": [
        "soil degradation", "soil erosion", "soil depletion", "soil health",
        "topsoil loss", "agricultural degradation", "land degradation"
    ],
    "crop diversity": [
        "crop diversity", "agricultural biodiversity", "genetic diversity",
        "crop varieties", "heirloom varieties", "seed diversity"
    ],
    "food security": [
        "food security", "food insecurity", "food access", "food availability",
        "hunger", "malnutrition", "food systems", "nutrition security"
    ],
    "agroecology": [
        "agroecology", "ecological farming", "sustainable agriculture",
        "regenerative agriculture", "ecological principles", "farm ecology"
    ],
    "organic farming": [
        "organic farming", "organic agriculture", "chemical-free farming",
        "natural farming", "certified organic", "biological farming"
    ],
    "livestock emissions": [
        "livestock emissions", "animal agriculture", "methane emissions",
        "greenhouse gases", "cattle emissions", "agricultural emissions"
    ],
    "agro-industrial processing": [
        "agro-industrial processing", "food processing industry",
        "industrial agriculture", "agricultural processing", "food manufacturing"
    ],
    
    # SUGAR & SWEETENERS CATEGORY
    "added sugars": [
        "added sugars", "free sugars", "refined sugars", "sugar additives",
        "sweeteners", "sugar content", "hidden sugars"
    ],
    "high-fructose corn syrup": [
        "high-fructose corn syrup", "HFCS", "corn syrup", "fructose syrup",
        "industrial sweetener", "liquid sugar"
    ],
    "refined carbohydrates": [
        "refined carbohydrates", "processed carbs", "simple carbohydrates",
        "white flour", "refined grains", "stripped carbs"
    ],
    "artificial sweeteners": [
        "artificial sweeteners", "sugar substitutes", "non-caloric sweeteners",
        "aspartame", "sucralose", "saccharin", "sugar alternatives"
    ],
    "sugar-sweetened beverages": [
        "sugar-sweetened beverages", "SSBs", "soft drinks", "sodas",
        "sweet drinks", "sugary drinks", "liquid calories"
    ],
    "insulin spike": [
        "insulin spike", "blood sugar spike", "glucose spike", "glycemic response",
        "insulin response", "postprandial glucose"
    ],
    "fructose metabolism": [
        "fructose metabolism", "fructose processing", "liver fructose",
        "fructose pathways", "fruit sugar metabolism"
    ],
    "glycemic load": [
        "glycemic load", "GL", "glucose load", "carbohydrate impact",
        "blood sugar load", "glycemic burden"
    ],
    "sugar addiction": [
        "sugar addiction", "sugar cravings", "sweet addiction",
        "sugar dependency", "food addiction", "sugar withdrawal"
    ],
    "hidden sugars": [
        "hidden sugars", "concealed sugars", "disguised sugars",
        "sugar aliases", "sugar names", "stealth sugars"
    ],
    
    # AIR POLLUTION (METABOLIC CONNECTION) CATEGORY
    "particulate matter": [
        "particulate matter", "PM2.5", "PM10", "air particles",
        "fine particles", "ultrafine particles", "airborne particles"
    ],
    "oxidative stress": [
        "oxidative stress", "free radical damage", "cellular oxidation",
        "antioxidant defense", "reactive oxygen species", "ROS"
    ],
    "inflammation": [
        "inflammation", "inflammatory response", "chronic inflammation",
        "inflammatory markers", "systemic inflammation", "immune response"
    ],
    "endocrine-disrupting chemicals": [
        "endocrine-disrupting chemicals", "EDCs", "hormone disruptors",
        "chemical interference", "hormonal chemicals", "toxic chemicals"
    ],
    "metabolic dysregulation": [
        "metabolic dysregulation", "metabolic disruption", "metabolic imbalance",
        "metabolic dysfunction", "hormonal imbalance", "endocrine disruption"
    ],
    "respiratory-metabolic link": [
        "respiratory-metabolic link", "lung-metabolism connection",
        "breathing and metabolism", "respiratory health", "pulmonary function"
    ],
    "urban smog": [
        "urban smog", "city pollution", "metropolitan air quality",
        "urban air pollution", "smog formation", "photochemical smog"
    ],
    "toxic air exposure": [
        "toxic air exposure", "air toxins", "atmospheric pollutants",
        "airborne toxins", "environmental toxins", "air contamination"
    ],
    
    # WATER POLLUTION (METABOLIC CONNECTION) CATEGORY
    "heavy metals": [
        "heavy metals", "lead", "mercury", "cadmium", "arsenic",
        "toxic metals", "metal contamination", "metal poisoning"
    ],
    "nitrate contamination": [
        "nitrate contamination", "nitrates", "water nitrates",
        "agricultural runoff", "fertilizer contamination", "groundwater nitrates"
    ],
    "microplastics": [
        "microplastics", "plastic particles", "plastic pollution",
        "nanoplastics", "plastic contamination", "environmental plastics"
    ],
    "pesticide runoff": [
        "pesticide runoff", "agricultural runoff", "chemical runoff",
        "water contamination", "pesticide pollution", "chemical leaching"
    ],
    "endocrine disruptors": [
        "endocrine disruptors", "hormone disruptors", "EDCs",
        "hormonal chemicals", "chemical interference", "toxic chemicals"
    ],
    "toxic algal blooms": [
        "toxic algal blooms", "harmful algae", "algae toxins",
        "water blooms", "cyanobacteria", "blue-green algae"
    ],
    "drinking water safety": [
        "drinking water safety", "water quality", "safe drinking water",
        "water contamination", "water purity", "potable water"
    ],
    "bioaccumulation": [
        "bioaccumulation", "biomagnification", "toxic accumulation",
        "chemical buildup", "environmental persistence", "food chain contamination"
    ],
    "industrial effluents": [
        "industrial effluents", "industrial waste", "chemical discharge",
        "factory pollution", "industrial contamination", "wastewater"
    ]
}

def get_enhanced_tag_conditions(tag: str) -> Tuple[str, List[str]]:
    """
    Enhanced tag matching using keywords, content analysis, and semantic matching
    Returns SQL WHERE condition and parameters for better categorization
    """
    
    # Enhanced frontend tag mapping - maps frontend subcategories to database values and keywords
    frontend_tag_mappings = {
        # News subcategories
        'latest': ['latest', 'breaking', 'recent', 'new', 'current', 'breaking news', 'health updates'],
        'policy and regulation': [
            'health policy', 'healthcare policy', 'medical policy', 'public health policy',
            'government health', 'health regulation', 'medical regulation', 'healthcare regulation',
            'health law', 'medical law', 'healthcare law',
            'fda approval', 'drug approval', 'medical approval', 'clinical guidelines',
            'health standards', 'medical standards', 'healthcare standards',
            'health ministry', 'health department', 'public health department',
            'health scheme', 'medical scheme', 'healthcare scheme', 'government scheme',
            'cghs', 'ayushman bharat', 'health insurance policy',
            'medical establishment', 'hospital registration', 'clinic registration',
            'health surveillance', 'disease surveillance', 'public health surveillance',
            'health emergency', 'public health emergency', 'health alert',
            'vaccination policy', 'immunization policy', 'quarantine policy'
        ],
        'govt schemes': ['government', 'scheme', 'policy', 'public health', 'healthcare policy', 'govt', 'ayushman'],
        'international': ['international', 'global', 'world health', 'who', 'global health', 'pandemic'],
        
        # Disease subcategories
        'diabetes': ['diabetes', 'diabetic', 'blood sugar', 'glucose', 'insulin', 'type 2 diabetes', 'hyperglycemia'],
        'obesity': ['obesity', 'overweight', 'weight', 'bmi', 'weight management', 'adipose', 'fat'],
        'inflammation': ['inflammation', 'inflammatory', 'immune', 'cytokine', 'autoimmune', 'arthritis'],
        'cardiovascular': ['cardiovascular', 'heart', 'cardiac', 'heart disease', 'blood pressure', 'hypertension', 'cholesterol'],
        'liver': ['liver', 'hepatic', 'fatty liver', 'nafld', 'liver function', 'hepatitis'],
        'kidney': ['kidney', 'renal', 'dialysis', 'kidney disease', 'nephrology'],
        'thyroid': ['thyroid', 'hormone', 'endocrine', 'metabolism', 'hypothyroid', 'hyperthyroid'],
        'metabolic': ['metabolic', 'metabolism', 'metabolic syndrome', 'energy', 'biochemical'],
        'sleep disorders': ['sleep', 'insomnia', 'sleep disorder', 'circadian', 'sleep quality'],
        'skin': ['skin', 'dermatology', 'dermatitis', 'acne', 'eczema', 'psoriasis'],
        'eyes and ears': ['eyes', 'vision', 'hearing', 'ear', 'ophthalmology', 'optical', 'auditory'],
        'reproductive health': ['reproductive', 'fertility', 'pregnancy', 'maternal', 'gynecology', 'obstetrics'],
        
        # Solutions subcategories
        'nutrition': ['nutrition', 'diet', 'food', 'nutritional', 'dietary', 'nutrient', 'vitamin', 'mineral'],
        'fitness': ['fitness', 'exercise', 'workout', 'training', 'physical activity', 'gym', 'sports'],
        'lifestyle': ['lifestyle', 'wellness', 'health habits', 'life style', 'daily routine'],
        'wellness': ['wellness', 'wellbeing', 'health', 'self care', 'mindfulness', 'meditation'],
        'prevention': ['prevention', 'preventive', 'screening', 'early detection', 'preventive care', 'immunization'],
        
        # Food subcategories
        'natural food': ['natural', 'organic', 'whole food', 'unprocessed', 'farm fresh', 'natural food'],
        'organic food': ['organic', 'pesticide free', 'chemical free', 'organic farming', 'organic food'],
        'processed food': ['processed', 'ultra processed', 'packaged', 'artificial', 'preservatives'],
        'fish and seafood': ['fish', 'seafood', 'omega', 'marine', 'salmon', 'tuna', 'shellfish'],
        'food safety': ['food safety', 'foodborne', 'contamination', 'food hygiene', 'food poisoning'],
        
        # Audience subcategories
        'women': ['women', 'female', 'woman', 'maternal', 'pregnancy', 'menopause', 'gynecology'],
        'men': ['men', 'male', 'man', 'prostate', 'testosterone', 'masculine', 'paternal'],
        'children': ['children', 'pediatric', 'kids', 'child', 'infant', 'adolescent', 'youth'],
        'teenagers': ['teenager', 'adolescent', 'teen', 'young adult', 'puberty'],
        'seniors': ['senior', 'elderly', 'geriatric', 'aging', 'old age', 'retirement'],
        'athletes': ['athlete', 'sports', 'performance', 'training', 'competition', 'athletic'],
        'families': ['family', 'household', 'parent', 'parenting', 'family health'],
        
        # Trending subcategories
        'gut health': ['gut', 'microbiome', 'digestive', 'intestinal', 'probiotic', 'gut bacteria'],
        'mental health': ['mental health', 'depression', 'anxiety', 'stress', 'psychology', 'psychiatric'],
        'hormones': ['hormone', 'hormonal', 'endocrine', 'insulin', 'cortisol', 'estrogen', 'testosterone'],
        'addiction': ['addiction', 'substance abuse', 'dependency', 'alcoholism', 'drug abuse'],
        'sleep health': ['sleep', 'insomnia', 'sleep quality', 'circadian rhythm', 'sleep disorder'],
        'sexual wellness': ['sexual', 'sexuality', 'libido', 'sexual health', 'intimate health']
    }
    
    # Get keywords for the requested tag - check both exact match and ENHANCED_KEYWORDS
    keywords = frontend_tag_mappings.get(tag.lower(), ENHANCED_KEYWORDS.get(tag.lower(), []))
    
    # If no specific mapping found, try to find partial matches
    if not keywords:
        for mapped_tag, mapped_keywords in frontend_tag_mappings.items():
            if tag.lower() in mapped_tag or mapped_tag in tag.lower():
                keywords = mapped_keywords
                break
    
    # Basic tag matching (existing logic)
    tag_underscore = tag.replace(" ", "_")
    conditions = []
    params = []
    
    # Special handling for "policy and regulation" - be more specific but not overly restrictive
    if tag.lower() in ['policy and regulation', 'policy_and_regulation']:
        # For policy and regulation, include both explicit policy tags and policy-related content
        
        # 1. Match exact policy tags in JSON format
        conditions.append('(LOWER(tags) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?))')
        params.extend(['%"policy and regulation"%', '%"health policy"%'])
        
        # 2. Match subcategory field for policy_and_regulation
        conditions.append('LOWER(subcategory) = LOWER(?)')
        params.append('policy_and_regulation')
        
        # 3. Match title that explicitly mentions policy, regulation, government, or schemes
        policy_title_conditions = []
        policy_keywords = [
            'health policy', 'medical policy', 'healthcare policy', 'public health policy',
            'government health scheme', 'health regulation', 'medical regulation',
            'fda approval', 'health ministry', 'health department', 'cghs',
            'ayushman bharat', 'health insurance policy', 'medical establishment registration',
            'government scheme', 'public health department', 'health law', 'medical law'
        ]
        
        for keyword in policy_keywords:
            policy_title_conditions.append('LOWER(title) LIKE LOWER(?)')
            params.append(f'%{keyword}%')
        
        # Add title-based conditions
        if policy_title_conditions:
            conditions.append(f'({" OR ".join(policy_title_conditions)})')
        
        # Combine with OR logic for better results (changed from AND)
        final_condition = f'({" OR ".join(conditions)})'
        
        return final_condition, params
    
    # For all other tags, use the original logic
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
        # Keyword matching in tags - more comprehensive
        keyword_conditions = []
        for keyword in keywords[:10]:  # Increased to top 10 keywords for better matching
            keyword_conditions.extend([
                'LOWER(tags) LIKE LOWER(?)',
                'LOWER(tags) LIKE LOWER(?)'
            ])
            params.extend([f'%{keyword.lower()}%', f'%"{keyword.lower()}"%'])
        
        if keyword_conditions:
            conditions.append(f'({" OR ".join(keyword_conditions)})')
        
        # Content-based matching (title and summary) for top keywords
        content_conditions = []
        for keyword in keywords[:6]:  # Top 6 keywords for content matching
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
        self._initialized = False
        
    def _optimize_connection(self, conn):
        """Apply performance optimizations to connection"""
        # Performance optimizations while maintaining data freshness
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and speed

        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        conn.execute("PRAGMA optimize")  # Optimize database
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
    @contextmanager
    def get_connection(self):
        """Get an optimized database connection"""
        conn = None
        try:
            # Ensure database directory exists
            db_path = Path(self.database)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(
                self.database, 
                timeout=30.0, 
                check_same_thread=False,
                isolation_level=None  # Autocommit mode for better performance
            )
            
            self._optimize_connection(conn)
            yield conn
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                logger.error(f"❌ Cannot access database at {self.database}. Checking permissions and path...")
                # Try to create the directory and file
                try:
                    db_path = Path(self.database)
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    # Touch the file to create it
                    db_path.touch(exist_ok=True)
                    logger.info(f"✅ Created database file at {self.database}")
                except Exception as create_error:
                    logger.error(f"❌ Cannot create database file: {create_error}")
            raise e
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            raise e
        finally:
            if conn:
                conn.close()

# Global connection pool
connection_pool = SQLiteConnectionPool(DB_PATH)

def decode_html_entities(text: str) -> str:
    """
    Decode HTML entities in text to proper characters
    
    Args:
        text: Text that may contain HTML entities like &#039; or &amp;
        
    Returns:
        str: Text with HTML entities decoded to proper characters
    """
    if not text or not isinstance(text, str):
        return text
    
    # Decode HTML entities like &#039; -> ' and &amp; -> &
    return html.unescape(text)

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



def get_category_keywords() -> Dict:
    """Load category keywords from YAML file."""
    try:
        if CATEGORY_YAML_PATH.exists():
            with open(CATEGORY_YAML_PATH, 'r', encoding='utf-8') as file:
                category_data = yaml.safe_load(file) or {}
                logger.info(f"Loaded {len(category_data)} categories from {CATEGORY_YAML_PATH}")
                return category_data
        else:
            logger.warning(f"Category file not found: {CATEGORY_YAML_PATH}")
            return {
                "diseases": {"diabetes": [], "obesity": [], "cardiovascular": []},
                "news": {"recent_developments": [], "policy_and_regulation": []},
                "solutions": {"medical_treatments": [], "preventive_care": []},
                "food": {"nutrition_basics": [], "superfoods": []},
                "audience": {"women": [], "men": [], "children": []},
                "blogs_and_opinions": {"expert_opinions": [], "patient_stories": []}
            }
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
        return {}

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
    Optimized paginated article retrieval with search and filtering - NO CACHING, ALWAYS FRESH DATA
    """
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
                # Enhanced category mapping to include both main categories and their subcategories
                # This ensures main categories like "news" include all their subcategory articles like "policy_and_regulation"
                
                # Updated category mappings to match frontend menu structure exactly
                category_mappings = {
                    'news': {
                        'main_categories': ['news', 'policy', 'international_health'],
                        'subcategories': ['latest', 'policy_and_regulation', 'policy and regulation', 'govt_schemes', 'govt schemes', 'international', 'medical_journals', 'global_health_organizations']
                    },
                    'diseases': {
                        'main_categories': ['diseases', 'metabolism'],
                        'subcategories': ['diabetes', 'obesity', 'inflammation', 'cardiovascular', 'liver', 'kidney', 'thyroid', 'metabolic', 'metabolic_diseases', 'sleep_disorders', 'sleep disorders', 'skin', 'eyes_and_ears', 'eyes and ears', 'reproductive_health', 'reproductive health']
                    },
                    'solutions': {
                        'main_categories': ['fitness', 'lifestyle', 'nutrition'],
                        'subcategories': ['nutrition', 'fitness', 'lifestyle', 'wellness', 'prevention']
                    },
                    'food': {
                        'main_categories': ['nutrition', 'agriculture', 'environmental_health'],
                        'subcategories': ['natural_food', 'natural food', 'organic_food', 'organic food', 'processed_food', 'processed food', 'fish_and_seafood', 'fish and seafood', 'food_safety', 'food safety']
                    },
                    'audience': {
                        'main_categories': ['audience'],
                        'subcategories': ['women', 'men', 'children', 'teenagers', 'seniors', 'athletes', 'families']
                    },
                    'trending': {
                        'main_categories': ['international_health', 'healthcare_system', 'news'],
                        'subcategories': ['gut_health', 'gut health', 'mental_health', 'mental health', 'hormones', 'addiction', 'sleep_health', 'sleep health', 'sexual_wellness', 'sexual wellness']
                    },
                    'blogs_and_opinions': {
                        'main_categories': ['news', 'policy'],
                        'subcategories': ['policy_and_regulation', 'policy and regulation', 'international', 'opinion', 'blog', 'editorial']
                    }
                }
                
                # Get mapping for the requested category
                mapping = category_mappings.get(category.lower(), {
                    'main_categories': [category],
                    'subcategories': []
                })
                
                main_categories = mapping.get('main_categories', [category])
                subcategories = mapping.get('subcategories', [])
                
                # Build comprehensive WHERE conditions
                category_conditions = []
                category_params = []
                
                # 1. Main category matching (check categories field - handles JSON arrays and strings)
                if category:
                    # Looser category mapping for more inclusive matching
                    category_mappings = {
                        'news': {
                            'main_categories': ['news', 'policy', 'international_health'],
                            'subcategories': ['latest', 'policy_and_regulation', 'policy and regulation', 'govt_schemes', 'govt schemes', 'international', 'medical_journals', 'global_health_organizations']
                        },
                        'diseases': {
                            'main_categories': ['diseases', 'metabolism'],
                            'subcategories': ['diabetes', 'obesity', 'inflammation', 'cardiovascular', 'liver', 'kidney', 'thyroid', 'metabolic', 'metabolic_diseases', 'sleep_disorders', 'sleep disorders', 'skin', 'eyes_and_ears', 'eyes and ears', 'reproductive_health', 'reproductive health']
                        },
                        'solutions': {
                            'main_categories': ['fitness', 'lifestyle', 'nutrition'],
                            'subcategories': ['nutrition', 'fitness', 'lifestyle', 'wellness', 'prevention']
                        },
                        'food': {
                            'main_categories': ['nutrition', 'agriculture', 'environmental_health'],
                            'subcategories': ['natural_food', 'natural food', 'organic_food', 'organic food', 'processed_food', 'processed food', 'fish_and_seafood', 'fish and seafood', 'food_safety', 'food safety']
                        },
                        'audience': {
                            'main_categories': ['audience'],
                            'subcategories': ['women', 'men', 'children', 'teenagers', 'seniors', 'athletes', 'families']
                        },
                        'trending': {
                            'main_categories': ['international_health', 'healthcare_system', 'news'],
                            'subcategories': ['gut_health', 'gut health', 'mental_health', 'mental health', 'hormones', 'addiction', 'sleep_health', 'sleep health', 'sexual_wellness', 'sexual wellness']
                        },
                        'blogs_and_opinions': {
                            'main_categories': ['news', 'policy'],
                            'subcategories': ['policy_and_regulation', 'policy and regulation', 'international', 'opinion', 'blog', 'editorial']
                        }
                    }
                    mapping = category_mappings.get(category.lower(), {
                        'main_categories': [category],
                        'subcategories': []
                    })
                    main_categories = mapping.get('main_categories', [category])
                    subcategories = mapping.get('subcategories', [])
                    category_conditions = []
                    category_params = []
                    # Main category matching (loose, substring match)
                    for mapped_cat in main_categories:
                        category_conditions.append("(LOWER(categories) LIKE LOWER(?))")
                        category_params.append(f'%{mapped_cat.lower()}%')
                    # Subcategory matching (loose, substring match)
                    for subcat in subcategories:
                        subcat_underscore = subcat.replace(" ", "_")
                        subcat_space = subcat.replace("_", " ")
                        category_conditions.append("(LOWER(subcategory) LIKE LOWER(?) OR LOWER(subcategory) LIKE LOWER(?))")
                        category_params.extend([f'%{subcat_underscore.lower()}%', f'%{subcat_space.lower()}%'])
                        # Also match in tags (JSON array as string)
                        category_conditions.append("(LOWER(tags) LIKE LOWER(?) OR LOWER(tags) LIKE LOWER(?))")
                        category_params.extend([f'%{subcat_underscore.lower()}%', f'%{subcat_space.lower()}%'])
                    if category_conditions:
                        where_conditions.append(f"({' OR '.join(category_conditions)})")
                        params.extend(category_params)
                        logger.info(f"🔍 Looser category filtering for '{category}' -> {len(main_categories)} main categories, {len(subcategories)} subcategories, {len(category_conditions)} total conditions")
            
            # Build where_clause string
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            # Optimized order clause - use indexed columns for better performance
            if sort_by.upper() == "DESC":
                # Use date DESC for chronological sorting
                order_clause = "ORDER BY date DESC"
            else:
                order_clause = "ORDER BY date ASC"

            # Optimized count query - use COUNT(1) for better performance
            if where_clause:
                count_query = f"SELECT COUNT(1) FROM articles {where_clause}"
                cursor.execute(count_query, params)
            else:
                # For no filters, use a faster approach
                cursor.execute("SELECT COUNT(1) FROM articles")

            total = cursor.fetchone()[0]
            logger.info(f"📊 Found {total} articles matching criteria")

            # Calculate pagination
            offset = (page - 1) * limit
            total_pages = (total + limit - 1) // limit

            # Ultra-optimized query - only essential columns
            query = f"""
                SELECT id, title, summary, url, source, date, categories as category, tags
                FROM articles 
                {where_clause} 
                {order_clause} 
                LIMIT ? OFFSET ?
            """

            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()
            
            # Ultra-fast article processing - minimal overhead
            articles = []
            for row in rows:
                article = dict(row)
                
                # Essential field validation only - fast check
                if not article.get('url') or not article.get('title') or len(article.get('url', '')) < 10:
                    continue
                
                # Minimal data cleaning
                article['title'] = article.get('title') or 'Untitled'
                article['summary'] = article.get('summary') or 'Health article summary'
                article['source'] = article.get('source') or 'Health News'
                
                # Fast tag parsing
                tags = article.get('tags', '')
                if tags and isinstance(tags, str):
                    try:
                        if tags.startswith('['):
                            article['tags'] = json.loads(tags)
                        else:
                            article['tags'] = [tag.strip() for tag in tags.split(',') if tag.strip()]
                    except:
                        article['tags'] = []
                else:
                    article['tags'] = []
                
                # Fast category parsing
                if article.get('category') and isinstance(article['category'], str):
                    try:
                        if article['category'].startswith('['):
                            categories_list = json.loads(article['category'])
                            article['category'] = categories_list[0] if categories_list else article['category']
                    except:
                        pass
                
                # Keep date as string for better performance
                articles.append(article)
            
            # METABOLIC HEALTH FILTERING: Apply metabolic health filter and deduplication
            # Only apply filtering if enabled in configuration
            # if config.is_metabolic_filter_enabled() or config.is_deduplication_enabled():
            #     logger.info(f"📋 Raw articles before filtering: {len(articles)}")
                
            #     # Apply filtering based on configuration
            #     if config.is_metabolic_filter_enabled() and config.is_deduplication_enabled():
            #         articles = filter_and_deduplicate_articles(articles)
            #         logger.info(f"📋 Articles after metabolic filtering and deduplication: {len(articles)}")
            #     elif config.is_metabolic_filter_enabled():
            #         articles = metabolic_filter.filter_articles(articles)
            #         logger.info(f"📋 Articles after metabolic filtering: {len(articles)}")
            #     elif config.is_deduplication_enabled():
            #         try:
            #             from .metabolic_filter import article_deduplicator
            #             articles = article_deduplicator.deduplicate_articles(articles)
            #             logger.info(f"📋 Articles after deduplication: {len(articles)}")
            #         except ImportError:
            #             logger.info("Deduplication unavailable - using fallback (no filtering)")
            #             logger.info(f"📋 Articles after deduplication: {len(articles)}")
            # else:
            #     logger.info(f"📋 Filtering disabled - returning {len(articles)} raw articles")
            
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

def get_category_stats() -> Dict[str, int]:
    """Get category statistics."""
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
                        if isinstance(categories_json, str):
                            categories_list = json.loads(categories_json)
                        else:
                            categories_list = categories_json
                        for category in categories_list:
                            if category in category_stats:
                                category_stats[category] += row['count']
                            else:
                                category_stats[category] = row['count']
                    except (json.JSONDecodeError, TypeError):
                        category_stats[categories_json] = row['count']
            return category_stats
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        return {}

def get_stats() -> Dict:
    """Get general statistics."""
    try:
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM articles WHERE date > date('now', '-7 days')")
            recent_articles = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT source) FROM articles")
            total_sources = cursor.fetchone()[0]
            category_stats = get_category_stats()
            stats = {
                "total_articles": total_articles,
                "recent_articles_7_days": recent_articles,
                "total_sources": total_sources,
                "total_categories": len(category_stats),
                "category_distribution": dict(list(category_stats.items())[:10]),
                "last_updated": datetime.now().isoformat()
            }
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
                       COALESCE(subcategory, '') as subcategory, tags, NULL as image_url, authors as author 
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
    """Initialize database optimizations and create tables if needed"""
    try:
        # Ensure database directory exists
        db_dir = Path(DB_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        with connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create articles table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    summary TEXT,
                    url TEXT UNIQUE NOT NULL,
                    categories TEXT,
                    tags TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    priority INTEGER DEFAULT 1,
                    url_health TEXT,
                    url_accessible INTEGER DEFAULT 1,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subcategory TEXT,
                    news_score REAL DEFAULT 0.0,
                    trending_score REAL DEFAULT 0.0,
                    content_quality_score REAL DEFAULT 0.0
                )
            ''')
            
            # Check if subcategory column exists, if not add it
            try:
                cursor.execute("SELECT subcategory FROM articles LIMIT 1")
            except sqlite3.OperationalError as e:
                if "no such column: subcategory" in str(e):
                    logger.info("Adding missing subcategory column to articles table")
                    cursor.execute("ALTER TABLE articles ADD COLUMN subcategory TEXT")
            
            # Check if other potentially missing columns exist and add them
            missing_columns = [
                ("news_score", "REAL DEFAULT 0.0"),
                ("trending_score", "REAL DEFAULT 0.0"),
                ("content_quality_score", "REAL DEFAULT 0.0"),
                ("url_health", "TEXT"),
                ("url_accessible", "INTEGER DEFAULT 1"),
                ("last_checked", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("priority", "INTEGER DEFAULT 1")
            ]
            
            for column_name, column_def in missing_columns:
                try:
                    cursor.execute(f"SELECT {column_name} FROM articles LIMIT 1")
                except sqlite3.OperationalError as e:
                    if f"no such column: {column_name}" in str(e):
                        logger.info(f"Adding missing {column_name} column to articles table")
                        cursor.execute(f"ALTER TABLE articles ADD COLUMN {column_name} {column_def}")
            
            # Create performance-optimized indexes
            indexes = [
                # Primary sorting indexes
                "CREATE INDEX IF NOT EXISTS idx_articles_id_desc ON articles(id DESC)",
                "CREATE INDEX IF NOT EXISTS idx_articles_date_desc ON articles(date DESC)",
                
                # Search and filter indexes
                "CREATE INDEX IF NOT EXISTS idx_articles_title_search ON articles(title COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_articles_summary_search ON articles(summary COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles(categories COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_articles_subcategory ON articles(subcategory COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles(tags COLLATE NOCASE)",
                "CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source COLLATE NOCASE)",
                
                # Compound indexes for common queries
                "CREATE INDEX IF NOT EXISTS idx_articles_cat_date ON articles(categories, date DESC)",
                "CREATE INDEX IF NOT EXISTS idx_articles_subcat_date ON articles(subcategory, date DESC)",
                
                # URL index for uniqueness checks
                "CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)",
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
                
            conn.commit()
            logger.info(f"✅ Database initialized successfully at: {DB_PATH}")
            
            # Check if database has articles
            cursor.execute("SELECT COUNT(*) FROM articles")
            article_count = cursor.fetchone()[0]
            logger.info(f"📊 Database contains {article_count} articles")
            
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        # Try to create a minimal database in a temporary location
        try:
            temp_db_path = "/tmp/articles.db" if Path("/tmp").exists() else "articles.db"
            # Update module-level DB_PATH
            import sys
            current_module = sys.modules[__name__]
            current_module.DB_PATH = temp_db_path
            logger.warning(f"🔄 Falling back to temporary database: {temp_db_path}")
            
            # Reinitialize connection pool with new path
            import sys
            current_module = sys.modules[__name__]
            current_module.connection_pool = SQLiteConnectionPool(temp_db_path)
            
            # Try again with temporary database
            with current_module.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS articles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        title TEXT NOT NULL,
                        authors TEXT,
                        summary TEXT,
                        url TEXT UNIQUE NOT NULL,
                        categories TEXT,
                        tags TEXT,
                        source TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        priority INTEGER DEFAULT 1,
                        url_health TEXT,
                        url_accessible INTEGER DEFAULT 1,
                        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        subcategory TEXT,
                        news_score REAL DEFAULT 0.0,
                        trending_score REAL DEFAULT 0.0,
                        content_quality_score REAL DEFAULT 0.0
                    )
                ''')
                conn.commit()
                logger.info(f"✅ Temporary database created successfully at: {temp_db_path}")
        except Exception as temp_error:
            logger.error(f"❌ Failed to create temporary database: {temp_error}")

def get_all_tags() -> List[str]:
    """Get all unique tags from the database - NO CACHING, ALWAYS FRESH DATA"""
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

def get_tags() -> List[str]:
    """Get list of all tags"""
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
        category_stats = get_category_stats()
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
        stats = get_stats()
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
    logger.info(f"🔧 Initializing database at: {DB_PATH}")
    
    # Initialize database and optimizations
    initialize_optimizations()
    
    # Pre-load categories
    get_category_keywords()
    
    logger.info("✅ Metabolical Backend utilities initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Could not fully initialize optimizations: {e}")
    logger.info("🔄 Application will continue with basic functionality")
