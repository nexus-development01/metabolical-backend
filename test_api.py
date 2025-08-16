#!/usr/bin/env python3
"""
Test API endpoints to verify our fixes
"""

import requests
import json

def test_api_endpoints():
    base_url = "http://127.0.0.1:8000/api/v1"
    
    print("Testing API endpoints with our fixes...")
    
    # Test search endpoint
    print("\n1. Testing search endpoint:")
    try:
        response = requests.get(f"{base_url}/search", params={"q": "diabetes", "limit": 3})
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {data['total']} articles")
            
            article_ids = []
            for i, article in enumerate(data['articles'], 1):
                print(f"   {i}. ID: {article['id']} - {article['title'][:60]}...")
                print(f"      Summary: {article['summary'][:100]}...")
                
                # Check for duplicates
                if article['id'] in article_ids:
                    print("      ⚠️  DUPLICATE ID!")
                else:
                    article_ids.append(article['id'])
                    
                # Check for generic summaries
                if any(phrase in article['summary'] for phrase in [
                    'Latest developments and breakthrough information',
                    'Comprehensive health information and insights'
                ]):
                    print("      ⚠️  GENERIC SUMMARY!")
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
    
    # Test category endpoint
    print("\n2. Testing category endpoint:")
    try:
        response = requests.get(f"{base_url}/category/diseases", params={"limit": 3})
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {data['total']} articles in diseases category")
            
            for i, article in enumerate(data['articles'], 1):
                print(f"   {i}. ID: {article['id']} - {article['title'][:60]}...")
                print(f"      Summary: {article['summary'][:100]}...")
        else:
            print(f"   ❌ Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")

if __name__ == "__main__":
    test_api_endpoints()
