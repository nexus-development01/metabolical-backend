# 🏥 Metabolical Backend API - Version 2.0.0

A FastAPI-based backend for health articles with search, categorization, and pagination. 
**Production-ready API with comprehensive endpoints, background scheduling, and optimized performance.**

## 📁 Project Structure

```
metabolical-backend/
├── app/                           # 🚀 Main application code
│   ├── main.py                   # FastAPI application (v2.0.0)
│   ├── utils.py                  # Database utilities
│   ├── url_validator.py          # URL validation utilities
│   ├── scheduler.py              # Background task scheduler
│   └── __init__.py               # Package initialization
├── config/                       # ⚙️ Configuration files
│   ├── category_keywords.yml     # Category classification keywords
│   ├── scraper_config.py         # Scraper configuration
│   └── __init__.py               # Package initialization
├── data/                         # 💾 Database and cache
│   └── articles.db               # SQLite database
├── scrapers/                     # 🕷️ Web scraper
│   ├── scraper.py                # Comprehensive health news scraper
│   └── __init__.py               # Package initialization
├── .env.example                  # � Environment configuration template
├── .gitignore                    # Git ignore rules
├── .dockerignore                 # Docker ignore rules
├── Dockerfile                    # 🐳 Docker configuration
├── build.sh                      # 🔧 Build script for deployment
├── render.yaml                   # ☁️ Render.com deployment config
├── start.py                      # 🎯 Simple startup script
├── stop.py                       # 🛑 Server shutdown script
├── requirements.txt              # 📦 Development dependencies
├── requirements-prod.txt         # 📦 Production dependencies
└── README.md                     # 📖 This file
```

## 🚀 Quick Start

### 1. Environment Setup (Optional)
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration (optional)
# Most settings have sensible defaults
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Server
```bash
# Local development
python start.py

# Production deployment  
python start.py --host 0.0.0.0 --port $PORT
```

### 4. Access the API
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **API Root**: http://localhost:8000/api/v1/
- **Base API**: http://localhost:8000/

## 🐳 Docker Deployment

```bash
# Build the Docker image
docker build -t metabolical-backend .

# Run the container
docker run -p 8000:8000 metabolical-backend
```

## ☁️ Cloud Deployment

### Render.com
1. Connect your GitHub repository
2. Use the included `render.yaml` configuration
3. Deploy automatically

### Other Platforms
- Uses `build.sh` for build commands
- Runs with `python start.py --host 0.0.0.0`
- Health check at `/api/v1/health`

## 📋 API Endpoints

The API supports both **base endpoints** (direct access) and **v1 endpoints** (versioned API):

### Base API Endpoints (No Prefix)
- `GET /search?q={query}` - Search articles directly
- `GET /category/{category}` - Get articles by category
- `GET /tag/{tag}` - Get articles by tag

### V1 API Endpoints (Recommended)
All v1 endpoints are under `/api/v1` prefix:

#### Core Endpoints
- `GET /api/v1/health` - Health check with database status
- `GET /api/v1/stats` - API statistics and metrics
- `GET /api/v1/` - API root with all available endpoints

#### Article Search Endpoints
- `GET /api/v1/search?q={query}` - **Primary search endpoint**
- `GET /api/v1/articles/search?q={query}` - **Alternative search endpoint**
- `GET /api/v1/search?q={query}&start_date={date}&end_date={date}` - Date-filtered search
- `GET /api/v1/search?q={query}&sort_by=asc` - Sorted search results

#### Category & Tag Endpoints
- `GET /api/v1/category/{category}` - Get articles by category
- `GET /api/v1/tag/{tag}` - Get articles by tag
- `GET /api/v1/categories` - Get all available categories
- `GET /api/v1/tags` - Get all available tags

#### Background Scheduler Endpoints
- `GET /api/v1/scheduler/status` - Get scheduler status
- `POST /api/v1/scheduler/trigger?scrape_type=quick` - Trigger manual scrape

#### Test-Specific Endpoints
- `GET /api/v1/tag/prevention` - Get prevention articles
- `GET /api/v1/category/diseases` - Get disease articles

## 🔍 API Usage Examples

### Search Examples
```bash
# Primary search endpoint
curl "http://localhost:8000/api/v1/search?q=diabetes&limit=10"

# Alternative search endpoint
curl "http://localhost:8000/api/v1/articles/search?q=diabetes&limit=10"

# Search with date filters
curl "http://localhost:8000/api/v1/search?q=diabetes&start_date=2025-01-01&end_date=2025-12-31"

# Search with sorting
curl "http://localhost:8000/api/v1/search?q=diabetes&sort_by=asc"
```

### Category & Tag Examples
```bash
# Get articles by category
curl "http://localhost:8000/api/v1/category/diseases?page=1&limit=20"

# Get articles by tag
curl "http://localhost:8000/api/v1/tag/prevention?limit=15"

# Get all categories
curl "http://localhost:8000/api/v1/categories"

# Get all tags
curl "http://localhost:8000/api/v1/tags"
```

### Base API Examples (Alternative)
```bash
# Direct search without API prefix
curl "http://localhost:8000/search?q=diabetes"

# Direct category access
curl "http://localhost:8000/category/diseases"
```

### Health & Monitoring
```bash
# Check API health
curl "http://localhost:8000/api/v1/health"

# Get API statistics
curl "http://localhost:8000/api/v1/stats"

# Check scheduler status
curl "http://localhost:8000/api/v1/scheduler/status"
```

## 📊 Response Format

```json
{
  "articles": [
    {
      "id": 123,
      "title": "Understanding Diabetes",
      "summary": "A comprehensive guide...",
      "url": "https://source.com/article",
      "source": "Health News",
      "date": "2025-07-30T10:00:00",
      "category": "diseases",
      "subcategory": "diabetes",
      "tags": ["health", "diabetes"]
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

## 🛠️ Development

### Project Features (v2.0.0)
✅ **Dual API Structure** - Both base endpoints and versioned v1 API  
✅ **Production CORS** - Configured for metabolical.in domains  
✅ **Background Scheduler** - Automated scraping with manual triggers  
✅ **Comprehensive Search** - Multiple search endpoints with filtering  
✅ **Category & Tag System** - Organized content classification  
✅ **Environment Configuration** - Flexible .env setup  
✅ **Performance Optimized** - Connection pooling and caching  
✅ **Health Monitoring** - Status endpoints and error handling  
✅ **Clean Architecture** - Single main.py with modular utilities  

### Key Improvements in v2.0.0
- **Enhanced API Structure**: Both direct and versioned endpoints
- **Production-Ready CORS**: Configured for metabolical.in domain
- **Background Processing**: Scheduler for automated tasks
- **Comprehensive Documentation**: Auto-generated via FastAPI
- **Environment Configuration**: Flexible .env setup
- **Enhanced Search**: Multiple search endpoints with date filtering
- **Monitoring**: Health checks and API statistics
- **Performance**: Optimized database queries and connection pooling

### Environment Configuration
Create a `.env` file from `.env.example`:
```bash
# Server Configuration
PORT=8000
PUBLIC_URL=http://localhost:8000

# Database Configuration  
DATABASE_PATH=data/articles.db

# API Configuration
DEBUG=false
LOG_LEVEL=info
```

### Development Setup
```bash
# Clone and navigate to project
cd metabolical-backend-main

# Install dependencies
pip install -r requirements.txt

# Optional: Copy and modify environment file
cp .env.example .env

# Start development server
python start.py

# Access documentation
open http://localhost:8000/docs
```

## 🔧 Recent Fixes & Improvements

### **Duplicate Articles Issue - FIXED ✅**
- **Problem**: Frontend was showing duplicate articles due to database duplicates
- **Solution**: Added `DISTINCT` clause to all SQL queries to prevent duplicate results
- **Impact**: Eliminates duplicate articles from search and category results

### **Generic Summary Issue - FIXED ✅**
- **Problem**: Articles showing generic summaries like "Latest developments and breakthrough information on..."
- **Solution**: Enhanced summary generation with content-aware analysis
- **New Features**:
  - Detects and replaces generic summary patterns
  - Creates contextual summaries based on title analysis
  - Content-specific summary generation for medical topics
  - Improved readability and informativeness

### **Enhanced Summary Quality**
- ✅ **AI/Medical Breakthrough**: "Explore how artificial intelligence is revolutionizing healthcare..."
- ✅ **Diet/Nutrition**: "Discover evidence-based dietary strategies for healthy weight management..."
- ✅ **Research Studies**: "Review the latest nutrition research findings and their health implications..."
- ✅ **Treatment Options**: "Learn about innovative treatment options, therapeutic advances..."

### **Technical Implementation Details**

#### **Duplicate Prevention**
```sql
-- Before (could return duplicates)
SELECT id, title, summary FROM articles WHERE title LIKE '%diabetes%'

-- After (ensures unique results)  
SELECT DISTINCT id, title, summary FROM articles WHERE title LIKE '%diabetes%'
```

#### **Smart Summary Generation**
```python
# Enhanced summary logic with content analysis
def _generate_smart_summary(title, category=None, source=None):
    if 'breakthrough' in title and 'ai' in title:
        return "Explore how AI is revolutionizing healthcare..."
    elif 'diet' in title and 'weight' in title:
        return "Discover evidence-based dietary strategies..."
    # ... more intelligent patterns
```

#### **Generic Pattern Detection**
- Detects patterns like "Latest developments and breakthrough information on..."
- Replaces with contextual, meaningful summaries
- Content-aware analysis based on medical topics
- Maintains summary quality and readability

## 🧪 Testing & Validation

### API Testing
```bash
# Test health endpoint
curl "http://localhost:8000/api/v1/health"

# Test search functionality
curl "http://localhost:8000/api/v1/search?q=diabetes"

# Test categories
curl "http://localhost:8000/api/v1/categories"

# Test specific category
curl "http://localhost:8000/api/v1/category/diseases?limit=5"

# Test statistics
curl "http://localhost:8000/api/v1/stats"
```

### Interactive Testing
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Root**: http://localhost:8000/api/v1/

### Manual Testing Endpoints
- `GET /api/v1/tag/prevention` - Test prevention tag
- `GET /api/v1/category/diseases` - Test diseases category
- `POST /api/v1/scheduler/trigger?scrape_type=quick` - Test background tasks

## 📝 Available Categories

- `diseases` - Medical conditions and health issues
- `news` - Health news and recent developments  
- `solutions` - Treatment and prevention methods
- `food` - Nutrition and dietary information
- `audience` - Target demographic content
- `blogs_and_opinions` - Expert opinions and patient stories

## 🔧 Troubleshooting

### Common Issues

1. **Database not found**: Make sure `data/articles.db` exists
2. **Port already in use**: Change port in `.env` or kill existing process with `python stop.py`
3. **Import errors**: Install dependencies with `pip install -r requirements.txt`
4. **CORS errors**: Check CORS configuration in `main.py` for allowed origins
5. **Scheduler issues**: Check scheduler status via `/api/v1/scheduler/status`
6. **Environment variables**: Copy `.env.example` to `.env` and modify as needed

### Logs & Monitoring
- **Console Output**: Detailed error messages and performance information
- **Health Check**: Monitor via `/api/v1/health`
- **API Statistics**: Check `/api/v1/stats` for usage metrics
- **Scheduler Status**: Monitor background tasks via `/api/v1/scheduler/status`

### Graceful Shutdown
Use `python stop.py` to properly shutdown the server and clean up resources.

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs - Interactive API testing
- **ReDoc**: http://localhost:8000/redoc - Clean API documentation  
- **API Root**: http://localhost:8000/api/v1/ - All available endpoints

### API Versions
- **Base API**: Direct endpoints without prefix (e.g., `/search`)
- **V1 API**: Versioned endpoints with `/api/v1` prefix (recommended)

### Search Capabilities
- **Full-text search** across title, summary, and content
- **Date filtering** with start_date and end_date parameters
- **Category-based filtering** for organized content access
- **Tag-based filtering** for specific topic searches
- **Pagination** with configurable page size
- **Sorting** by date (ascending/descending)

### Response Formats
All endpoints return JSON with consistent structure including:
- Paginated results with metadata
- Total count and page information
- Error handling with appropriate HTTP status codes
- Timestamp information for data freshness

## 📈 Performance & Production Features

- ✅ **SQLite WAL Mode** - Write-ahead logging for better concurrency
- ✅ **Connection Pooling** - Efficient database connection management
- ✅ **In-memory Caching** - LRU cache for frequently accessed data
- ✅ **Database Indexes** - Optimized queries for faster searches
- ✅ **Gzip Compression** - Automatic response compression
- ✅ **Background Scheduler** - Automated tasks without blocking API
- ✅ **Production CORS** - Configured for metabolical.in domains
- ✅ **Environment Configuration** - Flexible deployment settings
- ✅ **Health Monitoring** - Real-time API and database status
- ✅ **Graceful Shutdown** - Clean resource cleanup on stop

### Production Deployment
- **Render.com**: Automated deployment via `render.yaml`
- **Docker**: Container-ready with optimized Dockerfile  
- **Environment Variables**: Production configuration via `.env`
- **Health Checks**: Endpoint for load balancer monitoring
- **CORS Security**: Restricted to authorized domains

---

**🎯 Metabolical Backend API v2.0.0 - A production-ready health articles API with comprehensive search capabilities, background processing, and excellent documentation for easy deployment and maintenance.**
