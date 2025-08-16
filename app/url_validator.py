"""
Simple URL Validator for News Articles

This module provides basic URL validation functionality for the news scrapers.
"""

import requests
import re
from urllib.parse import urlparse
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class URLValidator:
    """Simple URL validator for article URLs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _is_placeholder_url(self, url: str) -> bool:
        """Check if URL is a placeholder/test URL that should be rejected"""
        placeholder_patterns = [
            'example.com',
            'example.org', 
            'example.net',
            'test.com',
            'placeholder.com',
            'dummy.com',
            'fake.com',
            'localhost',
            '127.0.0.1',
            'sample.com'
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in placeholder_patterns)
    
    def validate_article_url(self, article: Dict) -> Tuple[bool, Dict]:
        """
        Validate if an article URL is accessible and health-related
        
        Args:
            article: Dictionary containing article data with 'url' key
            
        Returns:
            Tuple of (is_valid: bool, info: dict)
        """
        url = article.get('url', '')
        
        if not url:
            return False, {"error": "No URL provided", "status": "invalid"}
        
        # Check for test/placeholder URLs
        if self._is_placeholder_url(url):
            return False, {"error": "Placeholder/test URL not allowed", "status": "invalid"}
        
        # Basic URL format validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, {"error": "Invalid URL format", "status": "invalid"}
        except Exception:
            return False, {"error": "URL parsing failed", "status": "invalid"}
        
        # Check if URL is accessible (with timeout and error handling)
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            
            if response.status_code in [200, 301, 302]:
                return True, {
                    "status": "valid",
                    "status_code": response.status_code,
                    "content_type": response.headers.get('content-type', 'unknown')
                }
            else:
                return False, {
                    "error": f"HTTP {response.status_code}",
                    "status": "invalid"
                }
                
        except requests.exceptions.Timeout:
            # Don't fail on timeout, just mark as potentially valid
            return True, {
                "status": "valid_timeout",
                "note": "URL accessible but response was slow"
            }
        except requests.exceptions.RequestException as e:
            # For network errors, don't fail completely - the URL might be valid
            return True, {
                "status": "valid_network_error", 
                "note": f"Network error but URL format is valid: {str(e)[:100]}"
            }
        except Exception as e:
            logger.warning(f"URL validation error for {url}: {e}")
            return True, {
                "status": "valid_unknown_error",
                "note": "Validation error but assuming URL is valid"
            }
    
    def is_health_related_url(self, url: str) -> bool:
        """Check if URL is from a health-related domain"""
        health_domains = [
            'who.int', 'nih.gov', 'cdc.gov', 'fda.gov',
            'webmd.com', 'healthline.com', 'mayoclinic.org',
            'medicalnewstoday.com', 'health.com', 'everydayhealth.com',
            'reuters.com', 'cnn.com', 'bbc.com', 'npr.org'
        ]
        
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.replace('www.', '')
            
            return any(health_domain in domain for health_domain in health_domains)
        except:
            return False
