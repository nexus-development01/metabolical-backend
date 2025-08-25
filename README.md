# 🏥 Metabolical Backend API - Version 2.1.0

A production-ready FastAPI backend f# Database operates automatically with the API
# Articles are stored with automatic duplicate prevention
# SQLite database with optimized schema and indexing
```

### Example API Usage:
````s with intelligent search, automated categorization, background scraping, and comprehensive database management.

## ⭐ Key Features

✅ **Duplicate-Free Content** - Intelligent deduplication ensures unique articles  
✅ **Smart Categorization** - AI-powered content classification  
✅ **Background Scraping** - Automated content collection from 20+ health sources  
✅ **Advanced Search** - Full-text search with filtering and pagination  
✅ **Production Ready** - Optimized for deployment with health monitoring  
✅ **Database Management** - Comprehensive tools for maintenance and optimization  

## 📁 Project Structure

```
metabolical-backend/
├── app/                           # 🚀 Core Application
│   ├── main.py                   # FastAPI application with dual API structure
│   ├── utils.py                  # Database utilities and search functions
│   ├── url_validator.py          # URL validation and health checks
│   ├── scheduler.py              # Background task scheduler
│   └── __init__.py               # Package initialization
├── config/                       # ⚙️ Configuration
│   ├── config.yml                # Consolidated configuration (all settings)
│   └── __init__.py               # Package initialization
├── scrapers/                     # 🕷️ Content Collection
│   ├── scraper.py                # Enhanced health news scraper
│   └── __init__.py               # Package initialization
├── data/                         # 💾 Database Storage
│   └── articles.db               # SQLite database with optimized schema
├── start.py                      # 🎯 Server startup script
├── .env.example                  # 🔧 Environment configuration template
├── .gitignore                    # Git ignore rules
├── .dockerignore                 # Docker ignore rules
├── Dockerfile                    # 🐳 Container configuration
├── build.sh                      # 🔧 Build script for deployment
├── render.yaml                   # ☁️ Cloud deployment configuration
├── requirements.txt              # 📦 Python dependencies
└── README.md                     # 📖 Documentation
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

### 2. Database Management
```bash
# Basic health check
python -c "from app.main import app; print('✅ API is ready')"
```

### 3. Start the Server
```bash
# Development
python start.py

# Production
python start.py --host 0.0.0.0 --port $PORT
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

# Clean up duplicates and optimize
python manage_db.py clean
```

### Example Output:
```
🏥 DATABASE HEALTH REPORT
==================================================
Total Articles: 2,146
Database Size: 15.8 MB
Duplicate Urls: 0
Duplicate Titles: 0
Has Url Unique Constraint: True
✅ Database is healthy!
```

## 📋 API Endpoints

### V1 API Endpoints (Recommended)
All v1 endpoints are under `/api/v1` prefix:

#### 🔍 Search Endpoints
```bash
# Primary search
GET /api/v1/search?q={query}&page=1&limit=20

# Alternative search
GET /api/v1/articles/search?q={query}

# Date-filtered search
GET /api/v1/search?q={query}&start_date=2025-01-01&end_date=2025-12-31

# Sorted search
GET /api/v1/search?q={query}&sort_by=asc
```

#### 📂 Category & Tag Endpoints
```bash
# Browse by category
GET /api/v1/category/{category}

# Browse by tag
GET /api/v1/tag/{tag}

# List all categories
GET /api/v1/categories

# List all tags
GET /api/v1/tags
```

#### 🏥 Monitoring Endpoints
```bash
# Health check
GET /api/v1/health

# API statistics
GET /api/v1/stats

# Scheduler status
GET /api/v1/scheduler/status

# Trigger manual scrape
POST /api/v1/scheduler/trigger?scrape_type=quick
```

### Base API Endpoints (Direct Access)
```bash
GET /search?q={query}           # Direct search
GET /category/{category}        # Direct category access
GET /tag/{tag}                  # Direct tag access
```

## 🔍 Usage Examples

### Search Operations
```bash
# Search for diabetes articles
curl "http://localhost:8000/api/v1/search?q=diabetes&limit=10"

# Search with pagination
curl "http://localhost:8000/api/v1/search?q=nutrition&page=2&limit=5"

# Date-filtered search
curl "http://localhost:8000/api/v1/search?q=covid&start_date=2025-01-01"
```

### Category Browsing
```bash
# Get disease articles
curl "http://localhost:8000/api/v1/category/diseases?limit=15"

# Get nutrition solutions
curl "http://localhost:8000/api/v1/category/solutions"

# List all categories
curl "http://localhost:8000/api/v1/categories"
```

### Health Monitoring
```bash
# Check API health
curl "http://localhost:8000/api/v1/health"

# Get statistics
curl "http://localhost:8000/api/v1/stats"
```

## 📊 Response Format

All endpoints return JSON with consistent pagination:

```json
{
  "articles": [
    {
      "id": 123,
      "title": "Understanding Diabetes",
      "summary": "Comprehensive guide to diabetes management...",
      "url": "https://source.com/article",
      "source": "Health News",
      "date": "2025-08-25T10:00:00",
      "category": "diseases",
      "subcategory": "diabetes",
      "tags": ["health", "diabetes", "medical"]
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "total_pages": 8,
  "has_next": true,
  "has_previous": false
}
```

## 🐳 Deployment

### Docker
```bash
# Build image
docker build -t metabolical-backend .

# Run container
docker run -p 8000:8000 metabolical-backend
```

### Cloud Deployment (Render.com)
1. Connect GitHub repository
2. Use `render.yaml` configuration
3. Deploy automatically

### Environment Variables
```bash
PORT=8000                       # Server port
HOST=0.0.0.0                   # Server host (0.0.0.0 for production)
DEBUG=false                    # Debug mode
DATABASE_PATH=data/articles.db # Database location
PUBLIC_URL=https://api.example.com  # Public API URL
```

## 📈 Performance Features

- ✅ **SQLite WAL Mode** - Optimized concurrent access
- ✅ **Smart Indexing** - Multi-column indexes for fast queries
- ✅ **Connection Pooling** - Efficient database connections
- ✅ **Response Caching** - LRU cache for frequent requests
- ✅ **Background Processing** - Non-blocking scrapers
- ✅ **Gzip Compression** - Automatic response compression
- ✅ **Rate Limiting** - Protection against abuse

## 🔧 Configuration

### Categories Available
- `diseases` - Medical conditions and health issues
- `news` - Health news and recent developments
- `solutions` - Treatment and prevention methods
- `food` - Nutrition and dietary information
- `audience` - Target demographic content
- `blogs_and_opinions` - Expert opinions and patient stories

### Data Sources (20+ Health Sources)
- **Government**: WHO, CDC, NIH
- **Academic**: Harvard Health, Medical Research
- **News**: BBC Health, NPR Health, Reuters Health
- **Medical**: Medical Xpress, ScienceDaily
- **Specialized**: Nutrition research, diabetes news

## 🛡️ Data Quality & Integrity

### ✅ Duplicate Prevention
- **Database-level UNIQUE constraints** on URLs
- **Real-time duplicate detection** during scraping
- **Smart title normalization** to catch near-duplicates
- **Comprehensive cleanup tools** via `manage_db.py`

### ✅ Content Quality
- **URL validation** and accessibility checks
- **Smart summary generation** for better descriptions
- **Content categorization** using AI-powered classification
- **Source reliability** tracking and prioritization

### ✅ Performance Optimization
- **Multi-column database indexes** for fast searches
- **Query optimization** with DISTINCT clauses
- **Background processing** for non-blocking operations
- **Connection pooling** and caching strategies

## 🚨 Troubleshooting

### Common Issues & Solutions

1. **Database Issues**
   ```bash
   # Check database health
   python manage_db.py check
   
   # Fix schema and duplicates
   python manage_db.py fix
   ```

2. **Duplicate Articles**
   ```bash
   # Analyze duplicates
   python manage_db.py duplicates
   
   # Clean up duplicates
   python manage_db.py clean
   ```

3. **Server Issues**
   ```bash
   # Check server health
   curl "http://localhost:8000/api/v1/health"
   
   # Restart server (stop with Ctrl+C)
   python start.py
   ```

4. **Performance Issues**
   ```bash
   # View database statistics
   python manage_db.py stats
   
   # Optimize database
   python manage_db.py fix
   ```

### Health Monitoring
- **API Health**: `/api/v1/health` - Database connectivity and status
- **Statistics**: `/api/v1/stats` - Usage metrics and performance data
- **Scheduler**: `/api/v1/scheduler/status` - Background task monitoring

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Root**: http://localhost:8000/api/v1/

### Search Capabilities
- **Full-text search** across titles, summaries, and content
- **Date filtering** with flexible date ranges
- **Category and tag filtering** for organized browsing
- **Pagination** with configurable page sizes
- **Sorting** by date (ascending/descending)
- **Advanced filtering** by source, category, and tags

## 🔄 Recent Improvements (v2.1.0)

### ✅ Project Structure Cleanup
- **Consolidated database management** into single `manage_db.py` utility
- **Removed redundant files** (check_duplicates.py, cleanup_duplicates.py, etc.)
- **Added proper package structure** with `__init__.py` files
- **Enhanced environment configuration** with comprehensive settings

### ✅ Production Readiness
- **Comprehensive database tools** for maintenance and monitoring
- **Enhanced error handling** and logging throughout the application
- **Optimized project structure** for easy deployment and maintenance
- **Production-grade configuration** with detailed environment options

### ✅ Developer Experience
- **Single command database management** - `python manage_db.py [command]`
- **Clear project organization** with logical file grouping
- **Enhanced documentation** with practical examples
- **Simplified deployment** process with better configuration

---

**🎯 Metabolical Backend API v2.1.0 - A production-ready, duplicate-free health articles API with comprehensive database management and excellent developer experience.**
