# 🏥 Metabolical Backend API - Clean & Simplified

A FastAPI-based backend for health articles with search, categorization, and pagination. 
**Simplified project structure for easy understanding and maintenance.**

## 📁 Project Structure

```
metabolical-backend/
├── app/                           # 🚀 Main application code
│   ├── main.py                   # FastAPI application
│   ├── utils.py                  # Database utilities
│   ├── url_validator.py          # URL validation utilities
│   └── __init__.py               # Package initialization
├── config/                       # ⚙️ Configuration files
│   ├── category_keywords.yml     # Category classification keywords
│   ├── scraper_config.py         # Scraper configuration
│   └── __init__.py               # Package initialization
├── data/                         # 💾 Database and cache
│   └── articles.db               # SQLite database
├── scrapers/                     # 🕷️ Web scrapers
│   ├── comprehensive_news_scraper.py     # Main news scraper
│   ├── python313_compatible_scraper.py  # Python 3.13 compatible scraper
│   ├── simple_health_scraper.py         # Simple health articles scraper
│   ├── smart_news_aggregator.py         # Smart news aggregation
│   ├── social_media_scraper.py          # Social media content scraper
│   └── __init__.py                      # Package initialization
├── docs/                         # 📚 Documentation
│   ├── ALL_ENDPOINTS.md          # Complete API endpoints reference
│   ├── Endpoint.md               # Endpoint documentation
│   ├── PERFORMANCE_IMPROVEMENTS.md # Performance optimization guide
│   ├── SEARCH_ENDPOINTS.md       # Search functionality documentation
│   └── SMARTNEWS_AGGREGATION.md  # Smart news aggregation documentation
├── start.py                      # 🎯 Simple startup script
├── stop.py                       # 🛑 Server shutdown script
├── requirements.txt              # 📦 Project dependencies
└── README.md                     # 📖 This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure for Public Deployment (Optional)
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your configuration
# Set PORT=80 for standard web port
# Set PUBLIC_URL=https://yourdomain.com for your domain
```

### 3. Start the Server

#### Local Development:
```bash
# Normal mode (default port 8000)
python start.py --port 8000

# Debug mode with detailed logging
python start.py --debug --port 8000
```

#### Public Deployment:
```bash
# Production mode on port 80
python start.py --port 80 --public-url https://yourdomain.com

# With environment variables
PORT=80 PUBLIC_URL=https://yourdomain.com python start.py
```

### 4. Stop the Server
```bash
# Use the stop script to gracefully shutdown
python stop.py
```

### 5. Access the API

#### Local Development:
- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### Public Deployment:
- **API Base URL**: https://yourdomain.com
- **Interactive Docs**: https://yourdomain.com/docs
- **ReDoc**: https://yourdomain.com/redoc

## 📋 API Endpoints

All endpoints are under `/api/v1` prefix:

### Core Endpoints
- `GET /api/v1/health` - Health check
- `GET /api/v1/stats` - API statistics

### Article Endpoints
- `GET /api/v1/articles/` - Get paginated articles
- `GET /api/v1/articles/latest` - Get latest articles
- `GET /api/v1/articles/search?q={query}` - **Search articles** (primary)
- `GET /api/v1/articles/{category}` - Get articles by category
- `GET /api/v1/articles/{category}/{subcategory}` - Get articles by subcategory

### Category & Organization
- `GET /api/v1/categories` - Get all categories
- `GET /api/v1/search?q={query}` - Search articles (legacy)

## 🔍 Search Examples

```bash
# Search for diabetes articles
curl "http://localhost:8000/api/v1/articles/search?q=diabetes&limit=10"

# Get articles by category
curl "http://localhost:8000/api/v1/articles/diseases?page=1&limit=20"

# Get latest articles
curl "http://localhost:8000/api/v1/articles/latest?limit=5"
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

### Project Structure Benefits
✅ **Single main.py** - No confusion between multiple main files  
✅ **Single utils.py** - All utilities in one place  
✅ **Clear directories** - Organized by function  
✅ **Simple startup** - One command to run  
✅ **Clean dependencies** - Only essential packages  
✅ **Multiple scrapers** - Comprehensive data collection  
✅ **Complete documentation** - Well-documented API endpoints  

### Available Scrapers
- **comprehensive_news_scraper.py** - Main news article scraper
- **python313_compatible_scraper.py** - Python 3.13 compatible scraper
- **simple_health_scraper.py** - Focused health article scraper
- **smart_news_aggregator.py** - Intelligent news aggregation
- **social_media_scraper.py** - Social media content extraction

### Configuration
- **Database**: SQLite database in `data/articles.db`
- **Categories**: Configured in `config/category_keywords.yml`
- **Scraper Settings**: Configured in `config/scraper_config.py`
- **Logging**: INFO level by default (DEBUG with --debug flag)
- **CORS**: Enabled for all origins (development)

## 🧪 Testing

For comprehensive API testing and verification, refer to the documentation:
- **Complete Endpoints**: See `docs/ALL_ENDPOINTS.md` for all available endpoints
- **Search Documentation**: Check `docs/SEARCH_ENDPOINTS.md` for search functionality
- **Performance Guide**: Review `docs/PERFORMANCE_IMPROVEMENTS.md` for optimization details

```bash
# Test the API manually
curl "http://localhost:8000/api/v1/health"
curl "http://localhost:8000/api/v1/stats"
```

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
2. **Port already in use**: Change port in `start.py` or kill existing process with `python stop.py`
3. **Import errors**: Install dependencies with `pip install -r requirements.txt`
4. **Scraper issues**: Check `config/scraper_config.py` for scraper settings

### Logs
Check the console output for detailed error messages and performance information.

### Graceful Shutdown
Use `python stop.py` to properly shutdown the server and clean up resources.

## 📚 Documentation

For detailed information about the API, please refer to:
- **`docs/ALL_ENDPOINTS.md`** - Complete list of all API endpoints
- **`docs/SEARCH_ENDPOINTS.md`** - Search functionality documentation  
- **`docs/PERFORMANCE_IMPROVEMENTS.md`** - Performance optimization guide
- **`docs/SMARTNEWS_AGGREGATION.md`** - Smart news aggregation details

## 📈 Performance Features

- ✅ SQLite connection pooling
- ✅ Database indexes for faster queries
- ✅ In-memory caching for frequently accessed data
- ✅ Optimized pagination
- ✅ Gzip compression for responses

---

**🎯 This project provides a clean, well-documented health articles API with comprehensive scraping capabilities and excellent documentation for easy understanding and maintenance.**
