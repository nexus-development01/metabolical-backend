"""
Configuration for Metabolical Backend
"""

import os
from typing import Dict, Any

class Config:
    """Application configuration"""
    
    # Metabolic Health Filtering - Disabled by default for general health content
    ENABLE_METABOLIC_FILTER = os.getenv("ENABLE_METABOLIC_FILTER", "false").lower() == "true"
    METABOLIC_FILTER_THRESHOLD = float(os.getenv("METABOLIC_FILTER_THRESHOLD", "0.1"))
    
    # Deduplication Settings
    ENABLE_DEDUPLICATION = os.getenv("ENABLE_DEDUPLICATION", "true").lower() == "true"
    DEDUPLICATION_THRESHOLD = float(os.getenv("DEDUPLICATION_THRESHOLD", "0.85"))
    
    # Database Settings
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/articles.db")
    
    # API Settings
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration values"""
        return {
            "metabolic_filter_enabled": cls.ENABLE_METABOLIC_FILTER,
            "metabolic_filter_threshold": cls.METABOLIC_FILTER_THRESHOLD,
            "deduplication_enabled": cls.ENABLE_DEDUPLICATION,
            "deduplication_threshold": cls.DEDUPLICATION_THRESHOLD,
            "database_path": cls.DATABASE_PATH,
            "default_page_size": cls.DEFAULT_PAGE_SIZE,
            "max_page_size": cls.MAX_PAGE_SIZE,
            "log_level": cls.LOG_LEVEL
        }
    
    @classmethod
    def is_metabolic_filter_enabled(cls) -> bool:
        """Check if metabolic filtering is enabled"""
        return cls.ENABLE_METABOLIC_FILTER
    
    @classmethod
    def is_deduplication_enabled(cls) -> bool:
        """Check if deduplication is enabled"""
        return cls.ENABLE_DEDUPLICATION

# Global config instance
config = Config()
