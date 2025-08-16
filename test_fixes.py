#!/usr/bin/env python3
"""
Test script to verify our fixes for duplicates and generic summaries
"""

from app.utils import search_articles_optimized, get_articles_paginated_optimized
import json

def test_search_function():
    print("Testing search with our fixes...")
    result = search_articles_optimized('diabetes', limit=5)
    print(f"Found {result['total']} articles, showing {len(result['articles'])}:")
    print()

    article_ids = []
    for i, article in enumerate(result['articles'], 1):
        print(f"{i}. ID: {article['id']}")
        print(f"   Title: {article['title'][:80]}...")
        print(f"   Summary: {article['summary'][:120]}...")
        print(f"   Source: {article['source']}")
        
        # Check for duplicates
        if article['id'] in article_ids:
            print("   ⚠️  DUPLICATE ID DETECTED!")
        else:
            article_ids.append(article['id'])
        
        # Check for generic summaries
        if any(phrase in article['summary'] for phrase in [
            'Latest developments and breakthrough information',
            'Comprehensive health information and insights',
            'Learn about the latest research and insights'
        ]):
            print("   ⚠️  GENERIC SUMMARY DETECTED!")
        
        print("   ---")

def test_category_function():
    print("\nTesting category search...")
    result = get_articles_paginated_optimized(category='diseases', limit=5)
    print(f"Found {result['total']} articles in diseases category, showing {len(result['articles'])}:")
    print()

    article_ids = []
    for i, article in enumerate(result['articles'], 1):
        print(f"{i}. ID: {article['id']}")
        print(f"   Title: {article['title'][:80]}...")
        print(f"   Summary: {article['summary'][:120]}...")
        
        # Check for duplicates
        if article['id'] in article_ids:
            print("   ⚠️  DUPLICATE ID DETECTED!")
        else:
            article_ids.append(article['id'])
        
        print("   ---")

if __name__ == "__main__":
    test_search_function()
    test_category_function()
