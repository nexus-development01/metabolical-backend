# Metabolical Backend API - Complete Endpoint Reference

## 🌐 Base URL
- **Local Development**: `http://localhost:8000`
- **Production (Render)**: `https://your-app-name.onrender.com`

## 📚 Documentation
- **Interactive Docs**: `/docs` (Swagger UI)
- **Alternative Docs**: `/redoc` (ReDoc)

---

## 🔹 Base API Endpoints (No Prefix)

### Search Endpoints
```
GET /search?q={query}
GET /search?q={query}&start_date={date}&end_date={date}
GET /search?q={query}&page=2&limit=10
GET /search?q={query}&sort_by=asc
```

**Example:**
```
GET /search?q=diabetes
GET /search?q=diabetes&start_date=2024-01-01&end_date=2024-12-31
GET /search?q=diabetes&page=1&limit=20&sort_by=desc
```

### Category Endpoints
```
GET /category/{category}
GET /category/{category}?page=2&limit=10
GET /category/{category}?sort_by=asc
```

**Example:**
```
GET /category/diseases
GET /category/diseases?page=2&limit=10
GET /category/diseases?sort_by=asc
```

### Tag Endpoints
```
GET /tag/{tag}
GET /tag/{tag}?page=2&limit=10
GET /tag/{tag}?sort_by=asc
```

**Example:**
```
GET /tag/prevention
GET /tag/prevention?page=2&limit=10
GET /tag/prevention?sort_by=asc
```

---

## 🔹 V1 API Endpoints (Preferred Version)

### Search Endpoints
```
GET /api/v1/articles/search?q={query}
GET /api/v1/search?q={query}
GET /api/v1/articles/search?q={query}&start_date={date}&end_date={date}
GET /api/v1/search?q={query}&start_date={date}&end_date={date}
GET /api/v1/category/{category}?page=2&limit=10
GET /api/v1/tag/{tag}?page=2&limit=10
GET /api/v1/articles/search?q={query}&sort_by=asc
GET /api/v1/search?q={query}&sort_by=asc
```

**Example:**
```
GET /api/v1/articles/search?q=diabetes
GET /api/v1/search?q=diabetes
GET /api/v1/articles/search?q=diabetes&start_date=2024-01-01&end_date=2024-12-31
GET /api/v1/search?q=diabetes&start_date=2024-01-01&end_date=2024-12-31
GET /api/v1/articles/search?q=diabetes&sort_by=asc
GET /api/v1/search?q=diabetes&sort_by=asc
```

### Category Endpoints
```
GET /api/v1/category/{category}
GET /api/v1/category/{category}?page=2&limit=10
```

**Example:**
```
GET /api/v1/category/diseases
GET /api/v1/category/diseases?page=2&limit=10
```

### Tag Endpoints
```
GET /api/v1/tag/{tag}
GET /api/v1/tag/{tag}?page=2&limit=10
```

**Example:**
```
GET /api/v1/tag/prevention
GET /api/v1/tag/prevention?page=2&limit=10
```

---

## 🔹 Test-Specific Endpoints

```
GET /api/v1/tag/prevention
GET /api/v1/category/diseases
```

**Example:**
```
GET /api/v1/tag/prevention
GET /api/v1/category/diseases
```

---

## 🔹 Utility Endpoints

### System Information
```
GET /api/v1/health          # Health check
GET /api/v1/categories      # List all categories
GET /api/v1/tags           # List all tags
GET /api/v1/stats          # API statistics
GET /                      # Root endpoint info
GET /api/v1/               # V1 API info
```

### 🔹 Scheduler Endpoints (NEW!)

```
GET /api/v1/scheduler/status                    # Get scheduler status
POST /api/v1/scheduler/trigger?scrape_type=quick # Trigger manual scrape
POST /api/v1/scheduler/trigger?scrape_type=full  # Trigger full scrape
```

**Example:**
```
GET /api/v1/scheduler/status
POST /api/v1/scheduler/trigger?scrape_type=quick
POST /api/v1/scheduler/trigger?scrape_type=full
```

---

## 📋 Query Parameters

### Common Parameters
- **`q`** (required for search): Search query string
- **`page`** (optional): Page number (default: 1)
- **`limit`** (optional): Items per page (default: 20, max: 100)
- **`sort_by`** (optional): Sort order - `asc` or `desc` (default: desc)
- **`start_date`** (optional): Filter from date (YYYY-MM-DD format)
- **`end_date`** (optional): Filter to date (YYYY-MM-DD format)

### Path Parameters
- **`{category}`**: Category name (e.g., diseases, news, solutions, food)
- **`{tag}`**: Tag name (e.g., prevention, treatment, nutrition)
- **`{query}`**: Search query string

---

## 📊 Response Format

### Paginated Article Response
```json
{
  "articles": [
    {
      "id": 1,
      "title": "Article Title",
      "summary": "Article summary...",
      "content": "Full article content...",
      "url": "https://source.com/article",
      "source": "Source Name",
      "date": "2024-01-01T00:00:00",
      "category": "diseases",
      "subcategory": "diabetes",
      "tags": ["prevention", "treatment"],
      "image_url": "https://source.com/image.jpg",
      "author": "Author Name"
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

### Health Check Response
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "database_status": "connected",
  "total_articles": 1500
}
```

### Categories Response
```json
{
  "categories": ["diseases", "news", "solutions", "food"],
  "total": 4,
  "timestamp": "2024-01-01T00:00:00"
}
```

### Tags Response
```json
{
  "tags": ["prevention", "treatment", "nutrition"],
  "total_tags": 3,
  "timestamp": "2024-01-01T00:00:00"
}
```

### Scheduler Status Response
```json
{
  "scheduler": {
    "is_running": true,
    "last_full_scrape": "2025-08-12T12:42:55.321997",
    "last_quick_scrape": "2025-08-12T12:43:59.390515",
    "next_full_scrape": "2025-08-13T00:42:55.321997",
    "next_quick_scrape": "2025-08-12T16:43:59.390515"
  },
  "timestamp": "2025-08-12T12:43:57.339297"
}
```

### Scheduler Trigger Response
```json
{
  "message": "Quick scrape triggered",
  "scrape_type": "quick",
  "triggered_at": "2025-08-12T12:43:59.390515"
}
```

---

## 🔒 CORS Configuration

The API is configured to accept requests from:
- `https://www.metabolical.in`
- `https://metabolical.in`
- `http://localhost:3000` (development)
- `http://localhost:3001` (development)

---

## 🧪 Testing

### Test Individual Endpoints
```bash
# Test health check
curl https://your-app.onrender.com/api/v1/health

# Test search
curl "https://your-app.onrender.com/api/v1/search?q=diabetes&limit=5"

# Test category
curl "https://your-app.onrender.com/api/v1/category/diseases?page=1&limit=10"
```

### Run Comprehensive Tests
```bash
# Test all endpoints locally
python test_all_endpoints.py

# Test all endpoints on production
python test_all_endpoints.py https://your-app.onrender.com
```

---

## 📈 Rate Limits & Performance

- **No rate limits** currently implemented
- **Pagination**: Maximum 100 items per page
- **Caching**: Response caching implemented for better performance
- **Compression**: GZip compression enabled for responses > 1KB

---

## 🚨 Error Responses

### Common HTTP Status Codes
- **200**: Success
- **400**: Bad Request (invalid parameters)
- **404**: Not Found (invalid endpoint)
- **422**: Validation Error (invalid query parameters)
- **500**: Internal Server Error

### Error Response Format
```json
{
  "detail": "Error description",
  "status_code": 400
}
```