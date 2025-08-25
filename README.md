# 🏥 Metabolical Backend API 
A production-ready FastAPI backend for health article aggregation with intelligent search, automated categorization, background scraping, and comprehensive RSS feed management.

## ⭐ Key Features

✅ **Duplicate-Free Content** - Intelligent deduplication ensures unique articles  
✅ **Smart Categorization** - AI-powered content classification with 7+ categories  
✅ **Background Scraping** - Automated content collection from 20+ health sources  
✅ **Advanced Search** - Full-text search with filtering and pagination  
✅ **Production Ready** - Optimized for deployment with health monitoring  
✅ **Robust RSS Handling** - Advanced feed validation, retry logic, and error handling  
✅ **Consolidated Configuration** - Single YAML file for all settings  

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
