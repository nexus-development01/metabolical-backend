# 📚 METABOLICAL BACKEND - Complete API Reference

## 🔹 Frontend-Compatible Endpoints

### Base API Endpoints (No Prefix)
```
✅ GET /search?q={query}
✅ GET /category/{category}
✅ GET /tag/{tag}
✅ GET /search?q={query}&start_date={date}&end_date={date}
✅ GET /category/{category}?page=2&limit=10
✅ GET /tag/{tag}?page=2&limit=10
✅ GET /category/{category}?sort_by=asc
✅ GET /tag/{tag}?sort_by=asc
```

### V1 API Endpoints (Recommended)
```
✅ GET /api/v1/articles/search?q={query}
✅ GET /api/v1/search?q={query}
✅ GET /api/v1/category/{category}
✅ GET /api/v1/tag/{tag}
✅ GET /api/v1/articles/search?q={query}&start_date={date}&end_date={date}
✅ GET /api/v1/search?q={query}&start_date={date}&end_date={date}
✅ GET /api/v1/category/{category}?page=2&limit=10
✅ GET /api/v1/tag/{tag}?page=2&limit=10
✅ GET /api/v1/articles/search?q={query}&sort_by=asc
✅ GET /api/v1/search?q={query}&sort_by=asc
```

### Test-Specific Endpoints
```
✅ GET /api/v1/tag/prevention
✅ GET /api/v1/category/diseases
```

## 🔹 Additional Useful Endpoints

### Metadata Endpoints
```
🆕 GET /api/v1/categories          # Get all available categories
🆕 GET /api/v1/tags               # Get all available tags
🆕 GET /api/v1/stats              # Get database statistics
```

### System Health & Monitoring
```
🆕 GET /api/v1/health             # Service health check
🆕 GET /api/v1/scheduler/status   # Background scraper status
🆕 POST /api/v1/scheduler/trigger # Manually trigger scraping
```

### Root Endpoints
```
🆕 GET /                          # API documentation
🆕 GET /api/v1/                   # V1 API info
```

## 🔹 Query Parameters

### Common Parameters (All Endpoints)
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20, max: 100)
- `sort_by` (string): "asc" or "desc" (default: "desc")

### Search-Specific Parameters
- `q` (string): Search query
- `start_date` (string): Filter from date (YYYY-MM-DD)
- `end_date` (string): Filter to date (YYYY-MM-DD)

## 🔹 Response Format

All endpoints return consistent JSON:
```json
{
  "articles": [...],
  "total": 1234,
  "page": 1,
  "limit": 20,
  "total_pages": 62,
  "has_next": true,
  "has_prev": false
}
```

## 🔹 Enhanced Features

### Improved Categorization
- ✅ Case-insensitive category filtering
- ✅ Smart "latest" tag filtering with date prioritization
- ✅ Enhanced subcategory support
- ✅ Better tag matching with flexible formats

### RSS Source Coverage (16 Sources)
- ✅ BBC Health, CNN Health, NPR Health
- ✅ WebMD, Medical News Today, Healthline
- ✅ NIH, WHO, CDC official sources
- ✅ Medical journals and research sources

### Performance Optimizations
- ✅ Database connection pooling
- ✅ Optimized SQL queries with proper indexing
- ✅ Efficient pagination
- ✅ Background scraping every 4 hours
