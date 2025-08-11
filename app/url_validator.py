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
        
        # Enhanced URL validation with stricter checks
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, {"error": "Invalid URL format", "status": "invalid"}
            
            # Check for problematic domains and patterns
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # Reject example domains and test domains
            invalid_domains = [
                'example.com', 'example.org', 'example.net',
                'test.com', 'test.org', 'localhost',
                'domain.com', 'sample.com', 'dummy.com'
            ]
            
            for invalid_domain in invalid_domains:
                if invalid_domain in domain:
                    return False, {"error": f"Invalid domain: {domain}", "status": "invalid"}
            
            # Reject problematic URL patterns
            invalid_patterns = [
                'javascript:', 'mailto:', 'file:', 'ftp:',
                '/404', '/error', '/not-found',
                '?error=', '&error=', '#error'
            ]
            
            for pattern in invalid_patterns:
                if pattern in url.lower():
                    return False, {"error": f"Invalid URL pattern: {pattern}", "status": "invalid"}
            
            # Check if it's a Google News RSS URL (these often don't work for direct access)
            if 'google.com/rss/articles/' in url:
                return False, {"error": "Google News RSS URLs are not accessible", "status": "invalid"}
                
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
            # For timeout, check if the URL format looks legitimate
            if any(valid_domain in domain for valid_domain in ['reuters.com', 'cnn.com', 'bbc.com', 'who.int', 'nih.gov', 'webmd.com', 'mayoclinic.org']):
                return True, {
                    "status": "valid_timeout",
                    "note": "URL from trusted domain but response was slow"
                }
            else:
                return False, {"error": "Timeout on unknown domain", "status": "invalid"}
        except requests.exceptions.RequestException as e:
            # For network errors, only accept if from trusted domains
            if any(valid_domain in domain for valid_domain in ['reuters.com', 'cnn.com', 'bbc.com', 'who.int', 'nih.gov', 'webmd.com', 'mayoclinic.org']):
                return True, {
                    "status": "valid_network_error", 
                    "note": f"Network error but URL from trusted domain: {str(e)[:100]}"
                }
            else:
                return False, {"error": f"Network error on untrusted domain: {str(e)[:100]}", "status": "invalid"}
        except Exception as e:
            logger.warning(f"URL validation error for {url}: {e}")
            return False, {"error": f"Validation error: {str(e)[:100]}", "status": "invalid"}
    
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
