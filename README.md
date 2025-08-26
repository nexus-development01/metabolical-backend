# 🏥 Metabolical Backend API 
A production-ready FastAPI backend for health article aggregation with intelligent search, automated categorization, background scraping, and comprehensive RSS feed management.

## ⭐ Key Features

✅ **Enhanced Search Algorithm** - Category-aware search with relevance ranking  
✅ **Smart Categorization** - 10 distinct categories with keyword-based classification  
✅ **RSS Source Optimization** - 90% success rate with automatic broken feed removal  
✅ **Database Standardization** - Clean category formats and duplicate prevention  
✅ **Background Scraping** - Automated content collection from 21+ reliable health sources  
✅ **Advanced Search** - Full-text search with category mapping and priority ranking  
✅ **Production Ready** - Optimized for deployment with comprehensive health monitoring  
✅ **System Utilities** - Built-in maintenance tools and health diagnostics  
✅ **Consolidated Configuration** - Single YAML file for all settings  

## 📊 Current System Status (Updated: August 26, 2025)

- **📰 Total Articles**: 1,228 articles (fully categorized)
- **🎯 RSS Success Rate**: 90% (21/23 sources working)
- **📈 Recent Activity**: 458 articles added in last 7 days
- **🏷️ Categories**: 10 properly distributed categories
- **🔍 Search Quality**: Enhanced relevance algorithm active
- **💾 Database Health**: No duplicates, all articles categorized

### Category Distribution:
- **News**: 518 articles (42.2%) - Latest health developments
- **Diseases**: 406 articles (33.1%) - Medical conditions and research  
- **Solutions**: 109 articles (8.9%) - Treatment and prevention strategies
- **Audience**: 105 articles (8.6%) - Demographic-specific health content
- **Trending**: 53 articles (4.3%) - Current health trends
- **Food**: 16 articles (1.3%) - Nutrition and food safety
- **Blogs & Opinions**: 8 articles (0.7%) - Expert opinions and analysis
- **Fitness**: 7 articles (0.6%) - Exercise and physical wellness
- **Mental Health**: 3 articles (0.2%) - Psychological wellbeing
- **Nutrition**: 3 articles (0.2%) - Dietary guidance and research

## 📁 Project Structure

```
metabolical-backend-main/
├── app/                          # 🚀 Core Application
│   ├── main.py                   # FastAPI application with comprehensive endpoints
│   ├── utils.py                  # 🆕 UNIFIED utilities (API + System maintenance)
│   ├── url_validator.py          # URL validation and health checks
│   ├── scheduler.py              # Background task scheduler with async support
│   └── __init__.py               # Package initialization
├── config/                       # ⚙️ Configuration
│   ├── config.yml                # 🆕 Consolidated configuration (all settings)
│   └── category_keywords.yml     # Category classification keywords
├── scrapers/                     # 🕷️ Content Collection
│   ├── scraper.py                # Enhanced health news scraper (21 reliable sources)
│   └── __init__.py               # Package initialization
├── data/                         # 💾 Database Storage
│   └── articles.db               # SQLite database with optimized schema
├── start.py                      # 🎯 Server startup script
├── .env.example                  # 🔧 Environment configuration template
├── Dockerfile                    # 🐳 Container configuration
├── build.sh                      # 🔧 Build script for deployment
├── render.yaml                   # ☁️ Cloud deployment configuration
├── requirements.txt              # 📦 Python dependencies
└── README.md                     # 📖 This comprehensive documentation
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd metabolical-backend-main

# Install dependencies
pip install -r requirements.txt

# Optional: Configure environment
cp .env.example .env
# Edit .env file as needed
```

### 2. Verify Installation & System Health
```bash
# Test API functions
python -c "from app.utils import get_articles_paginated_optimized; print('✅ API utilities loaded')"

# Test system utilities
python -c "from app.utils import system_health_check; print('✅ System utilities loaded')"

# Basic health check
python -c "from app.main import app; print('✅ FastAPI is ready')"
```

### 3. Start the Server
```bash
# Development
python start.py

# Production with Gunicorn
gunicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access the API
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **API Root**: http://localhost:8000/api/v1/

## 🔍 Enhanced Search Functionality

### Search Algorithm Features:
✅ **Category-Aware Mapping**: Automatically maps search terms to relevant categories  
✅ **Relevance Prioritization**: Title matches > Summary matches > Tag matches  
✅ **Domain Intelligence**: Maps "food" to nutrition keywords, "fitness" to exercise terms  
✅ **Results Ranking**: Comprehensive scoring system for result relevance  

### Search Examples:
```bash
# Enhanced food search (returns nutrition-related content)
curl "http://localhost:8000/api/v1/search?q=food&limit=10"

# Fitness-focused search
curl "http://localhost:8000/api/v1/search?q=fitness&limit=5"

# Medical research search
curl "http://localhost:8000/api/v1/search?q=diabetes&category=diseases"
```

### Search Quality Improvements:
- **Before**: Searching "food" returned irrelevant results (Gaza famine articles)
- **After**: Returns relevant nutrition content (food safety, diet research, etc.)

## 🛠️ System Utilities & Maintenance

The system includes comprehensive built-in utilities for maintenance and monitoring:

### Available System Functions:
```python
from app.utils import (
    # System Health & Monitoring
    system_health_check,           # Comprehensive health diagnostics
    run_comprehensive_system_check, # Full system validation
    
    # Database Analysis
    check_category_distribution,    # Category statistics and analysis
    standardize_category_formats,   # Database cleanup and standardization
    
    # Testing & Validation
    test_search_functionality,      # Search algorithm testing
    validate_rss_sources,          # RSS feed health validation
    
    # API Functions (unchanged)
    get_articles_paginated_optimized, # Main article retrieval
    search_articles_optimized,      # Enhanced search with filtering
    get_category_stats_cached,      # Category statistics with caching
)
```

### System Health Check Example:
```python
from app.utils import system_health_check
import json

health = system_health_check()
print(json.dumps(health, indent=2))
```

**Sample Output:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-26T11:03:27.116562",
  "checks": {
    "database": {
      "status": "healthy",
      "total_articles": 1228
    },
    "duplicates": {
      "status": "healthy",
      "duplicate_count": 0
    },
    "categorization": {
      "status": "healthy", 
      "uncategorized_count": 0
    },
    "recent_activity": {
      "status": "healthy",
      "recent_articles_7_days": 458
    }
  }
}
```

## 🌐 RSS Feed Management & Optimization

### Current RSS Source Status (90% Success Rate):
✅ **Working Sources (21/23)**:
- WHO Health News
- BBC Health  
- NPR Health
- ScienceDaily Health
- Nature Medicine
- Harvard Nutrition Source
- Medical Research News
- WebMD Health News
- Reuters Health
- HealthDay News
- Shape Magazine Health
- Men's Health Magazine
- MindBodyGreen Blog
- Plus 8 more reliable sources...

❌ **Removed Broken Sources (3)**:
- NIH/PubMed Central News (404 errors)
- Prevention Magazine (Invalid RSS feed)
- Everyday Health (Connection issues)

### RSS Validation Features:
```python
from app.utils import validate_rss_sources

# Test RSS sources (returns detailed status)
result = validate_rss_sources(limit=15)
print(f"Success rate: {result['success_rate']}%")
print(f"Working sources: {result['working']}/{result['tested']}")
```

### RSS Error Handling:
- ✅ **Automatic retry logic** with exponential backoff
- ✅ **User-Agent rotation** to avoid bot detection  
- ✅ **Timeout handling** with graceful degradation
- ✅ **Failed source tracking** and automatic removal
- ✅ **Success rate monitoring** and reporting

## 📊 Database Management & Optimization

### Database Features:
- **Automatic duplicate prevention** using URL and title hashing
- **Optimized SQLite schema** with proper indexing
- **Category standardization** (removed format inconsistencies)
- **Built-in health monitoring** via API endpoints
- **WAL mode** for better concurrent access

### Database Statistics:
```python
from app.utils import check_category_distribution

stats = check_category_distribution()
print(f"Total articles: {stats['total_articles']}")
print(f"Categories: {len(stats['distribution'])}")
```

### Category Format Standardization:
The system automatically fixes inconsistent category formats:
- **Before**: `["diseases"]`, `["News"]`, `["solutions", "mental_health"]`
- **After**: `diseases`, `news`, `solutions`

## 🛡️ API Endpoints

### Core Endpoints
- `GET /api/v1/health` - Comprehensive health check with system diagnostics
- `GET /api/v1/search` - Enhanced search with category-aware ranking
- `GET /api/v1/articles` - Paginated article listing with filtering
- `GET /api/v1/articles/category/{category}` - Articles by category
- `GET /api/v1/categories` - Available categories with statistics
- `GET /api/v1/stats` - Database and system statistics

### Enhanced Search Examples:
```bash
# Category-aware food search
curl "http://localhost:8000/api/v1/search?q=food&limit=10"
# Returns: nutrition articles, food safety, diet research

# Fitness content search  
curl "http://localhost:8000/api/v1/search?q=fitness&limit=5"
# Returns: exercise articles, workout research, physical wellness

# Medical research with category filter
curl "http://localhost:8000/api/v1/search?q=diabetes&category=diseases&limit=10"
```

### Legacy Compatibility (Maintained)
- `GET /search` - Legacy search endpoint
- `GET /articles` - Legacy article listing
- `GET /categories` - Legacy categories

## 🔧 System Maintenance Commands

### Manual System Operations:
```python
# Category distribution analysis
from app.utils import check_category_distribution
result = check_category_distribution()

# Search functionality testing
from app.utils import test_search_functionality  
test_result = test_search_functionality(['food', 'nutrition', 'fitness'])

# RSS source validation
from app.utils import validate_rss_sources
rss_result = validate_rss_sources(limit=15)

# Database cleanup
from app.utils import standardize_category_formats
cleanup_result = standardize_category_formats()

# Comprehensive system check
from app.utils import run_comprehensive_system_check
full_report = run_comprehensive_system_check()
```

## 📈 Background Scraping

The scheduler runs automatically with optimized intervals:

- **Full Scrape**: Every 12 hours (comprehensive collection from all 21 sources)
- **Quick Scrape**: Every 15 minutes (priority sources only)
- **Parallel Processing**: Up to 5 concurrent sources
- **Smart Throttling**: Respectful delays and rate limiting
- **Error Recovery**: Automatic retry for failed sources

### Manual Scraping Triggers:
```bash
# Trigger manual scraping via API
curl -X POST "http://localhost:8000/api/v1/scraper/trigger?type=quick"
curl -X POST "http://localhost:8000/api/v1/scraper/trigger?type=full"
```

## 🧪 Testing & Validation

### System Testing:
```bash
# Test search functionality
python -c "
from app.utils import test_search_functionality
result = test_search_functionality(['food', 'nutrition'])
print('Search test:', result['status'])
"

# Test RSS sources
python -c "
from app.utils import validate_rss_sources  
result = validate_rss_sources(limit=10)
print(f'RSS success rate: {result[\"success_rate\"]}%')
"

# Full system health check
python -c "
from app.utils import system_health_check
health = system_health_check()
print('System status:', health['status'])
"
```

### API Testing:
```bash
# Test enhanced search
curl "http://localhost:8000/api/v1/search?q=food&limit=5"

# Test health endpoint
curl "http://localhost:8000/api/v1/health"

# Test category statistics
curl "http://localhost:8000/api/v1/categories"
```

## 🐳 Docker Deployment

```bash
# Build image
docker build -t metabolical-backend .

# Run container
docker run -p 8000:8000 metabolical-backend

# With environment variables
docker run -p 8000:8000 -e DEBUG=false metabolical-backend
```

## ☁️ Cloud Deployment (Render.com)

The included `render.yaml` provides one-click deployment:

```yaml
services:
  - type: web
    name: metabolical-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python start.py
```

## 🐛 Troubleshooting

### Common Issues & Solutions

1. **Search Results Not Relevant**
   ```bash
   # Test search algorithm
   python -c "
   from app.utils import test_search_functionality
   result = test_search_functionality(['food'])
   print('Search working:', result['status'] == 'success')
   "
   ```

2. **RSS Feed Issues**
   ```bash
   # Check RSS source health
   python -c "
   from app.utils import validate_rss_sources
   result = validate_rss_sources(limit=10)
   print(f'RSS health: {result[\"success_rate\"]}% success rate')
   "
   ```

3. **Database Issues**
   ```bash
   # Check database health
   python -c "
   from app.utils import system_health_check
   health = system_health_check()
   db_status = health['checks']['database']['status']
   print(f'Database status: {db_status}')
   "
   ```

4. **Category Distribution Problems**
   ```bash
   # Analyze categories
   python -c "
   from app.utils import check_category_distribution
   stats = check_category_distribution()
   print(f'Total articles: {stats[\"total_articles\"]}')
   print(f'Categories: {len(stats[\"distribution\"])}')
   "
   ```

5. **Performance Issues**
   ```bash
   # Full system diagnostic
   python -c "
   from app.utils import run_comprehensive_system_check
   report = run_comprehensive_system_check()
   print('System status:', report['status'])
   "
   ```

## 🔒 Security

- ✅ Input validation and sanitization
- ✅ Rate limiting on API endpoints  
- ✅ Secure HTTP headers
- ✅ Environment-based configuration
- ✅ SQL injection prevention
- ✅ RSS feed validation and sanitization

## 📈 Monitoring & Health Checks

### Built-in System Monitoring:
- **Database Health**: Connection, integrity, and performance checks
- **RSS Feed Status**: Source validation, success rates, and blacklist management
- **Search Quality**: Algorithm testing and relevance validation
- **Category Distribution**: Article categorization analysis
- **System Performance**: Memory, processing, and response time metrics
- **Error Tracking**: Comprehensive logging with structured error reporting

### Comprehensive Health Check Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-26T11:03:27.116562",
  "checks": {
    "health_check": {
      "status": "healthy",
      "checks": {
        "database": { "status": "healthy", "total_articles": 1228 },
        "duplicates": { "status": "healthy", "duplicate_count": 0 },
        "categorization": { "status": "healthy", "uncategorized_count": 0 },
        "recent_activity": { "status": "healthy", "recent_articles_7_days": 458 }
      }
    },
    "category_distribution": {
      "status": "success",
      "total_articles": 1228,
      "distribution": { "news": { "count": 518, "percentage": 42.2 } }
    },
    "search_test": {
      "status": "success", 
      "search_results": { "food": { "count": 5 }, "nutrition": { "count": 5 } }
    },
    "rss_validation": {
      "status": "success",
      "success_rate": 90.0,
      "working": 9,
      "failed": 1
    }
  }
}
```

## 🔄 Recent Improvements (v4.0 - August 2025)

### Major Enhancements:
✅ **Enhanced Search Algorithm**: Category-aware search with relevance ranking  
✅ **RSS Source Optimization**: Improved from 50% to 90% success rate  
✅ **Database Standardization**: Fixed 554 articles with inconsistent category formats  
✅ **Utility Consolidation**: All utilities merged into single `app/utils.py` file  
✅ **System Health Monitoring**: Comprehensive diagnostics and reporting  
✅ **Category Distribution**: Improved from 5 to 16+ articles in food category  
✅ **Search Quality**: "food" searches now return nutrition content instead of irrelevant news  

### File Structure Cleanup:
- **Removed redundant files**: 5+ utility files consolidated
- **Single source of truth**: All functions in `app/utils.py`
- **Better organization**: Clear separation between API and maintenance functions

### Performance Improvements:
- **Database optimization**: Proper indexing and WAL mode
- **RSS feed reliability**: Automatic broken source removal
- **Search relevance**: Enhanced algorithm with category intelligence
- **System monitoring**: Built-in health checks and diagnostics

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests using built-in utilities
4. Test with: `python -c "from app.utils import run_comprehensive_system_check; print(run_comprehensive_system_check())"`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- **System Health**: Use `python -c "from app.utils import system_health_check; print(system_health_check())"` 
- **Search Testing**: Use `python -c "from app.utils import test_search_functionality; print(test_search_functionality())"`
- **RSS Validation**: Use `python -c "from app.utils import validate_rss_sources; print(validate_rss_sources())"`
- **API Health Check**: Use `/api/v1/health` endpoint for comprehensive status
- **Documentation**: Check this README and `/docs` endpoint
- **Logs**: Check application logs for detailed error information

---

**Built with ❤️ for health information accessibility**  
**Current Version: 4.0** | **Last Updated: August 26, 2025** | **System Status: ✅ Healthy**  

## 📁 Project Structure

```
metabolical-backend-main/
├── app/                          # 🚀 Core Application
│   ├── main.py                   # FastAPI application with dual API structure
│   ├── utils.py                  # Database utilities and search functions
│   ├── url_validator.py          # URL validation and health checks
│   ├── scheduler.py              # Background task scheduler with async support
│   └── __init__.py               # Package initialization
├── config/                       # ⚙️ Configuration
│   └── config.yml                # 🆕 Consolidated configuration (all settings)
├── scrapers/                     # 🕷️ Content Collection
│   ├── scraper.py                # Enhanced health news scraper with robust RSS handling
│   └── __init__.py               # Package initialization
├── data/                         # 💾 Database Storage
│   └── articles.db               # SQLite database with optimized schema
├── start.py                      # 🎯 Server startup script
├── .env.example                  # 🔧 Environment configuration template
├── Dockerfile                    # 🐳 Container configuration
├── build.sh                      # 🔧 Build script for deployment
├── render.yaml                   # ☁️ Cloud deployment configuration
├── requirements.txt              # 📦 Python dependencies
└── README.md                     # 📖 This documentation
```

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd metabolical-backend-main

# Install dependencies
pip install -r requirements.txt

# Optional: Configure environment
cp .env.example .env
# Edit .env file as needed
```

### 2. Verify Installation
```bash
# Basic health check
python -c "from app.main import app; print('✅ API is ready')"
```

### 3. Start the Server
```bash
# Development
python start.py

# Production with Gunicorn
gunicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access the API
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **API Root**: http://localhost:8000/api/v1/

## 🛠️ Database Management

The database operates automatically with the API. Here are the key features:

- **Automatic duplicate prevention** using URL and title hashing
- **Optimized SQLite schema** with proper indexing
- **WAL mode** for better concurrent access
- **Built-in health monitoring** via API endpoints

### Example API Usage:
```bash
# Search for articles
curl "http://localhost:8000/api/v1/search?q=diabetes&limit=10"

# Get articles by category
curl "http://localhost:8000/api/v1/articles/category/chronic-diseases?limit=5"

# Health check
curl "http://localhost:8000/api/v1/health"
```

## 🔧 RSS Feed Management & Error Handling

### Current Feed Status & Issues

The scraper includes robust error handling for common RSS feed issues:

#### 🚨 **Known Issues Fixed in v3.0:**

1. **Dead/Invalid Feeds Handled:**
   - ❌ `https://www.sciencedaily.com/rss/health_medicine/environmental_health.xml` (404)
   - ❌ `https://www.eurekalert.org/rss/health_medicine.xml` (404)
   - ✅ **Solution**: Automatic feed validation with fallback sources

2. **403 Forbidden Errors Resolved:**
   - ❌ `https://www.medicalnewstoday.com/rss/nutrition.xml` (403 Forbidden)
   - ✅ **Solution**: Enhanced User-Agent headers and retry logic

3. **Network Reliability Improved:**
   - ✅ Exponential backoff retry mechanism
   - ✅ Timeout handling with graceful degradation
   - ✅ Connection pooling and session management

### 🔧 **Advanced RSS Features:**

#### **Robust Request Handling**
```python
# Enhanced headers to avoid bot detection
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9"
}

# Retry logic with exponential backoff
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[403, 404, 429, 500, 502, 503, 504]
)
```

#### **Smart Feed Validation**
- ✅ Pre-scraping feed validation
- ✅ Blacklist management for problematic feeds
- ✅ Alternative feed suggestions
- ✅ Automatic retry scheduling

#### **Structured Logging**
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
```

## 🐳 Docker Deployment

```bash
# Build image
docker build -t metabolical-backend .

# Run container
docker run -p 8000:8000 metabolical-backend

# With environment variables
docker run -p 8000:8000 -e DEBUG=false metabolical-backend
```

## ☁️ Cloud Deployment (Render.com)

The included `render.yaml` provides one-click deployment:

```yaml
services:
  - type: web
    name: metabolical-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python start.py
```

## 🔍 API Endpoints

### Core Endpoints
- `GET /api/v1/health` - Health check and system status
- `GET /api/v1/search` - Full-text search with filters
- `GET /api/v1/articles` - Paginated article listing
- `GET /api/v1/articles/category/{category}` - Articles by category
- `GET /api/v1/categories` - Available categories
- `GET /api/v1/stats` - Database statistics

### Legacy Compatibility
- `GET /search` - Legacy search endpoint
- `GET /articles` - Legacy article listing
- `GET /categories` - Legacy categories

## 📊 Background Scraping

The scheduler runs automatically and includes:

- **Full Scrape**: Every 12 hours (comprehensive collection)
- **Quick Scrape**: Every 15 minutes (priority sources only)
- **Parallel Processing**: Up to 5 concurrent sources
- **Smart Throttling**: Respectful delays and rate limiting

### Manual Triggers
```bash
# Trigger manual scraping via API
curl -X POST "http://localhost:8000/api/v1/scraper/trigger?type=quick"
curl -X POST "http://localhost:8000/api/v1/scraper/trigger?type=full"
```

## 🧪 Testing

```bash
# Test API endpoints
python -c "
import requests
resp = requests.get('http://localhost:8000/api/v1/health')
print('Status:', resp.status_code)
print('Response:', resp.json())
"

# Test search functionality
curl "http://localhost:8000/api/v1/search?q=health&limit=5"
```

## 🐛 Troubleshooting

### Common Issues

1. **Module Import Errors**
   ```bash
   # Ensure you're in the project directory
   cd metabolical-backend-main
   python -c "from app.main import app"
   ```

2. **Database Issues**
   ```bash
   # Check database status
   python -c "
   from app.utils import get_db_stats
   print(get_db_stats())
   "
   ```

3. **RSS Feed Issues**
   ```bash
   # Check feed validation status
   curl "http://localhost:8000/api/v1/health"
   ```

4. **Performance Issues**
   ```bash
   # Check system resources and database size
   python -c "
   import sqlite3
   conn = sqlite3.connect('data/articles.db')
   count = conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
   print(f'Articles in database: {count}')
   conn.close()
   "
   ```

5. **Network/RSS Connectivity**
   ```bash
   # Test RSS feed directly
   curl -H "User-Agent: Mozilla/5.0" "https://feeds.feedburner.com/reuters/health"
   ```

### Performance Optimization

- **Database Indexing**: Automatic on startup
- **Connection Pooling**: Built-in SQLite optimization
- **Caching**: In-memory duplicate detection
- **Parallel Processing**: Concurrent RSS fetching

## 🔒 Security

- ✅ Input validation and sanitization
- ✅ Rate limiting on API endpoints
- ✅ Secure HTTP headers
- ✅ Environment-based configuration
- ✅ SQL injection prevention

## 📈 Monitoring & Health Checks

### Built-in Monitoring
- **Database Health**: Connection and integrity checks
- **RSS Feed Status**: Feed validation and blacklist management
- **System Performance**: Memory and processing metrics
- **Error Tracking**: Structured logging with rotation

### Health Check Endpoint
```json
{
  "status": "healthy",
  "timestamp": "2025-08-25T10:30:00Z",
  "database": {
    "articles_count": 2146,
    "duplicates_count": 0,
    "categories_loaded": 7
  },
  "scraper": {
    "last_scrape": "2025-08-25T10:15:00Z",
    "active_feeds": 18,
    "blacklisted_feeds": 2
  }
}
```

## 🔄 Migration & Updates

### Version 3.0 Changes
- ✅ **Consolidated configuration** into single `config.yml`
- ✅ **Enhanced RSS error handling** with retry logic
- ✅ **Improved feed validation** and blacklist management
- ✅ **Better logging** and monitoring
- ✅ **Streamlined project structure**

### Upgrading from v2.x
1. **Configuration**: Old YAML files automatically consolidated
2. **Database**: Automatic schema updates on startup
3. **Dependencies**: Run `pip install -r requirements.txt`

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- **Documentation**: Check this README and `/docs` endpoint
- **Health Check**: Use `/api/v1/health` for system status
- **Logs**: Check application logs for detailed error information

---

**Built with ❤️ for health information accessibility**
