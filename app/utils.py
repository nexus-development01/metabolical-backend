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
from functools import lru_cache
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
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent))
    from metabolic_filter import filter_and_deduplicate_articles, metabolic_filter
    from config import config

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
        """Get a database connection with proper error handling"""
        conn = None
        try:
            # Ensure database directory exists
            db_path = Path(self.database)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.database, timeout=30.0, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.row_factory = sqlite3.Row  # Enable column access by name
            
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

# Cache for category keywords
_category_cache = {}
_stats_cache = {}
_cache_timestamp = None

def clear_all_caches():
    """Clear all application caches to ensure fresh data"""
    global _category_cache, _stats_cache, _cache_timestamp
    _category_cache.clear()
    _stats_cache.clear()
    _cache_timestamp = None
    logger.info("🗑️ All application caches cleared")

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
    Optimized paginated article retrieval with search and filtering
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
                # Map frontend categories to database categories and enhanced search
                category_mappings = {
                    # Frontend category -> Database categories and related content
                    'food': ['nutrition', 'lifestyle'],  # Map 'food' to nutrition and lifestyle
                    'solutions': ['fitness', 'lifestyle', 'nutrition'],  # Map 'solutions' to fitness, lifestyle, nutrition
                    'blogs_and_opinions': ['news', 'policy'],  # Map 'blogs_and_opinions' to news and policy
                    'trending': ['international_health', 'healthcare_system'],  # Map 'trending' to international_health and healthcare_system
                    'news': ['news'],
                    'diseases': ['diseases'],
                    'audience': ['audience']
                }
                
                # Get mapped categories for the requested category
                mapped_categories = category_mappings.get(category.lower(), [category])
                
                # Create conditions for all mapped categories
                category_conditions = []
                category_params = []
                
                for mapped_cat in mapped_categories:
                    # Direct category match
                    category_conditions.append("(LOWER(categories) = LOWER(?) OR LOWER(categories) LIKE LOWER(?))")
                    category_params.extend([mapped_cat, f'%{mapped_cat}%'])
                
                # For special frontend categories, also search in content
                if category.lower() in ['food', 'solutions', 'blogs_and_opinions', 'trending']:
                    content_keywords = {
                        'food': ['food', 'nutrition', 'diet', 'eating', 'meal', 'recipe', 'cooking', 'ingredient'],
                        'solutions': ['treatment', 'therapy', 'cure', 'solution', 'prevention', 'remedy', 'exercise', 'fitness'],
                        'blogs_and_opinions': ['opinion', 'blog', 'editorial', 'commentary', 'analysis', 'perspective'],
                        'trending': ['trending', 'latest', 'breakthrough', 'new study', 'recent', 'innovation']
                    }
                    
                    keywords = content_keywords.get(category.lower(), [])
                    if keywords:
                        keyword_conditions = []
                        for keyword in keywords[:5]:  # Limit to top 5 keywords
                            keyword_conditions.append("(LOWER(title) LIKE LOWER(?) OR LOWER(summary) LIKE LOWER(?))")
                            category_params.extend([f'%{keyword}%', f'%{keyword}%'])
                        
                        if keyword_conditions:
                            category_conditions.append(f"({' OR '.join(keyword_conditions)})")
                
                # Combine all category conditions
                if category_conditions:
                    where_conditions.append(f"({' OR '.join(category_conditions)})")
                    params.extend(category_params)
                    logger.info(f"🔍 Enhanced filtering for category: '{category}' -> mapped to {mapped_categories} with content search")
                
            if tag:
                # Use enhanced categorization system
                enhanced_condition, enhanced_params = get_enhanced_tag_conditions(tag)
                
                # Special handling for "latest" - add date filter for recent articles only
                if tag.lower() == "latest":
                    # Get current date and recent dates (last 2 days)
                    current_date = datetime.now()
                    yesterday = current_date - timedelta(days=1)
                    day_before = current_date - timedelta(days=2)
                    
                    # Format dates for matching
                    today_str = current_date.strftime('%Y-%m-%d')
                    yesterday_str = yesterday.strftime('%Y-%m-%d')
                    day_before_str = day_before.strftime('%Y-%m-%d')
                    
                    # Only include articles from last 2 days for "latest"
                    date_condition = f"""(
                        date LIKE '%{today_str}%' OR 
                        date LIKE '%{yesterday_str}%' OR
                        date LIKE '%{day_before_str}%'
                    )"""
                    final_condition = f"({enhanced_condition} AND {date_condition})"
                    where_conditions.append(final_condition)
                    params.extend(enhanced_params)
                    logger.info(f"🏷️ Enhanced filtering for LATEST tag with {len(enhanced_params)} conditions + date filter (last 2 days: {day_before_str} to {today_str})")
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
            
            # Order clause - improved date sorting to handle different date formats
            if sort_by.upper() == "DESC":
                # Enhanced sorting: prioritize recent dates with proper timestamp ordering
                order_clause = """ORDER BY 
                    CASE 
                        WHEN date LIKE '%2025-08-08%' THEN 1
                        WHEN date LIKE '%2025-08-07%' THEN 2
                        WHEN date LIKE '%2025-08-06%' THEN 3
                        WHEN date LIKE '%2025-08-05%' THEN 4
                        WHEN date LIKE '%2025%' THEN 5
                        WHEN date LIKE '%2024%' THEN 6
                        ELSE 7
                    END ASC,
                    CASE 
                        WHEN date LIKE '%2025-08-08%' OR date LIKE '%2025-08-07%' THEN 
                            datetime(substr(date, 1, 19))
                        WHEN date LIKE '%2025%' THEN 
                            datetime(date)
                        ELSE date
                    END DESC,
                    id DESC"""
            else:
                order_clause = f"ORDER BY datetime(date) ASC, id ASC"
            
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
                       COALESCE(subcategory, '') as subcategory, tags, NULL as image_url, authors as author 
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
                
                # Decode HTML entities in all text fields
                text_fields = ['title', 'summary', 'source', 'category', 'tags']
                for field in text_fields:
                    if article.get(field):
                        article[field] = decode_html_entities(article[field])
                
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
                
                # Clean up outdated "Latest" tags based on article date
                if isinstance(article['tags'], list):
                    # Check if article has a "Latest" or "Breaking" tag (including multi-word variants)
                    has_latest = any(
                        any(keyword in tag.lower() for keyword in ['latest', 'breaking'])
                        for tag in article['tags']
                    )
                    
                    if has_latest:
                        # Check if article is actually recent (last 2 days)
                        article_date = article.get('date')
                        is_recent = False
                        
                        if article_date:
                            try:
                                if isinstance(article_date, str):
                                    # Parse the date string
                                    article_dt = datetime.fromisoformat(article_date.replace('Z', '+00:00'))
                                else:
                                    article_dt = article_date
                                
                                # Check if article is from last 2 days
                                current_date = datetime.now()
                                two_days_ago = current_date - timedelta(days=2)
                                is_recent = article_dt.date() >= two_days_ago.date()
                                
                            except (ValueError, AttributeError) as e:
                                logger.debug(f"Error parsing date for article {article.get('id')}: {e}")
                                is_recent = False
                        
                        # Remove "Latest" tags if article is not recent
                        if not is_recent:
                            original_tags = article['tags'].copy()
                            # Remove tags containing 'latest' or 'breaking' (case insensitive)
                            article['tags'] = [
                                tag for tag in article['tags']
                                if not any(keyword in tag.lower() for keyword in ['latest', 'breaking'])
                            ]
                            
                            if len(original_tags) != len(article['tags']):
                                logger.debug(f"Removed outdated 'Latest/Breaking' tag from article {article.get('id')} dated {article_date}")
                                
                                # Add 'News' tag if no other meaningful tags remain
                                if not article['tags'] or all(tag.lower() in ['news'] for tag in article['tags']):
                                    if 'News' not in article['tags']:
                                        article['tags'].append('News')
                    
                # Parse date
                if article.get('date'):
                    try:
                        article['date'] = datetime.fromisoformat(article['date'].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        article['date'] = datetime.now()
                        
                articles.append(article)
            
            # METABOLIC HEALTH FILTERING: Apply metabolic health filter and deduplication
            # Only apply filtering if enabled in configuration
            if config.is_metabolic_filter_enabled() or config.is_deduplication_enabled():
                logger.info(f"📋 Raw articles before filtering: {len(articles)}")
                
                # Apply filtering based on configuration
                if config.is_metabolic_filter_enabled() and config.is_deduplication_enabled():
                    articles = filter_and_deduplicate_articles(articles)
                    logger.info(f"📋 Articles after metabolic filtering and deduplication: {len(articles)}")
                elif config.is_metabolic_filter_enabled():
                    articles = metabolic_filter.filter_articles(articles)
                    logger.info(f"📋 Articles after metabolic filtering: {len(articles)}")
                elif config.is_deduplication_enabled():
                    from .metabolic_filter import article_deduplicator
                    articles = article_deduplicator.deduplicate_articles(articles)
                    logger.info(f"📋 Articles after deduplication: {len(articles)}")
            else:
                logger.info(f"📋 Filtering disabled - returning {len(articles)} raw articles")
            
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
    
    # Cache for 1 minute only (reduced from 5 minutes for fresher data)
    if _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < 60:
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
    
    # Cache for 1 minute only (reduced from 5 minutes for fresher data)
    if _cache_timestamp and (datetime.now() - _cache_timestamp).seconds < 60:
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
            
            # Create indexes if they don't exist
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date)",
                "CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles(categories)",
                "CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)",
                "CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title)",
                "CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)",
                "CREATE INDEX IF NOT EXISTS idx_articles_tags ON articles(tags)",
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

def get_tags_cached() -> List[str]:
    """Get cached list of all tags - Cache disabled for fresh data"""
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
    logger.info(f"🔧 Initializing database at: {DB_PATH}")
    
    # Initialize database and optimizations
    initialize_optimizations()
    
    # Pre-load categories
    get_cached_category_keywords()
    
    logger.info("✅ Metabolical Backend utilities initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Could not fully initialize optimizations: {e}")
    logger.info("🔄 Application will continue with basic functionality")
