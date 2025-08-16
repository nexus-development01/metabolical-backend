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
