"""
Metabolical Backend API - Clean and Simplified
Health articles API with search, categorization, and pagination.
"""

from fastapi import FastAPI, HTTPException, Query, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import utilities
try:
    from .utils import *
    from .scheduler import scheduler
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent))
    from utils import *
    from scheduler import scheduler

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Metabolical Backend API...")
    
    # Start the background scheduler
    try:
        scheduler.start()
        logger.info("Background scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Metabolical Backend API...")
    try:
        scheduler.stop()
        logger.info("Background scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

# FastAPI app
app = FastAPI(
    title="Metabolical Backend API",
    description="Health articles API with search, categorization, and pagination",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS configuration for production
allowed_origins = [
    "https://www.metabolical.in",
    "https://metabolical.in",
    "http://127.0.0.1:3000",  # Alternative localhost
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

# Load categories on startup
try:
    CATEGORY_KEYWORDS = get_cached_category_keywords()
    CATEGORIES = list(CATEGORY_KEYWORDS.keys())
except Exception as e:
    logger.warning(f"Could not load categories: {e}")
    CATEGORIES = ["news", "diseases", "solutions", "food", "audience", "trending", "blogs_and_opinions"]

# Pydantic Models
class ArticleSchema(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    url: str
    source: Optional[str] = None
    date: datetime
    category: Optional[str] = None
    subcategory: Optional[str] = None
    tags: List[str] = []
    author: Optional[str] = None

class PaginatedArticleResponse(BaseModel):
    articles: List[ArticleSchema]
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_previous: bool

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database_status: str
    total_articles: Optional[int] = None

# =============================================
# BASE API ENDPOINTS (NO PREFIX)
# =============================================

@app.get("/search", response_model=PaginatedArticleResponse)
def search_articles_base(
    q: str = Query(..., description="Search query", min_length=2),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """Search articles - Base endpoint without prefix"""
    try:
        logger.info(f"Base Search: '{q}', page: {page}, limit: {limit}")
        
        result = search_articles_optimized(
            query=q,
            page=page,
            limit=limit,
            sort_by=sort_by,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Base Search '{q}' result: {result['total']} total, {len(result['articles'])} returned")
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in search_articles_base: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/category/{category}", response_model=PaginatedArticleResponse)
def get_articles_by_category_base(
    category: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by category - Base endpoint without prefix"""
    try:
        logger.info(f"Base Category request: '{category}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            category=category
        )
        
        logger.info(f"Base Category '{category}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in get_articles_by_category_base: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/tag/{tag}", response_model=PaginatedArticleResponse)
def get_articles_by_tag_base(
    tag: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by tag - Base endpoint without prefix"""
    try:
        logger.info(f"Base Tag request: '{tag}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            tag=tag
        )
        
        logger.info(f"Base Tag '{tag}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in get_articles_by_tag_base: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================
# V1 API ENDPOINTS (PREFERRED VERSION)
# =============================================

# Create API Router
v1_router = APIRouter(prefix="/api/v1", tags=["API v1"])

@v1_router.get("/")
@v1_router.get("")  # Also handle /api/v1 without trailing slash
def api_v1_root():
    """API v1 Root - Available endpoints"""
    return {
        "message": "Metabolical Backend API v1",
        "version": "2.0.0",
        "endpoints": {
            "search": "/api/v1/search?q={query}",
            "articles_search": "/api/v1/articles/search?q={query}",
            "search_with_dates": "/api/v1/search?q={query}&start_date={date}&end_date={date}",
            "articles_search_with_dates": "/api/v1/articles/search?q={query}&start_date={date}&end_date={date}",
            "search_sorted": "/api/v1/search?q={query}&sort_by=asc",
            "articles_search_sorted": "/api/v1/articles/search?q={query}&sort_by=asc",
            "category": "/api/v1/category/{category}",
            "category_paginated": "/api/v1/category/{category}?page=2&limit=10",
            "tag": "/api/v1/tag/{tag}",
            "tag_paginated": "/api/v1/tag/{tag}?page=2&limit=10",
            "categories": "/api/v1/categories",
            "tags": "/api/v1/tags",
            "stats": "/api/v1/stats",
            "health": "/api/v1/health",
            "scheduler_status": "/api/v1/scheduler/status",
            "scheduler_trigger": "/api/v1/scheduler/trigger?scrape_type=quick",
            "test_prevention": "/api/v1/tag/prevention",
            "test_diseases": "/api/v1/category/diseases"
        },
        "documentation": "/docs",
        "status": "active"
    }

@v1_router.get("/articles/search", response_model=PaginatedArticleResponse)
def search_articles_v1_articles(
    q: str = Query(..., description="Search query", min_length=2),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """Search articles - V1 articles endpoint"""
    try:
        logger.info(f"V1 Articles Search: '{q}', page: {page}, limit: {limit}")
        
        result = search_articles_optimized(
            query=q,
            page=page,
            limit=limit,
            sort_by=sort_by,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"V1 Articles Search '{q}' result: {result['total']} total, {len(result['articles'])} returned")
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in search_articles_v1_articles: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/search", response_model=PaginatedArticleResponse)
def search_articles_v1(
    q: str = Query(..., description="Search query", min_length=2),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """Search articles - V1 endpoint"""
    try:
        logger.info(f"V1 Search: '{q}', page: {page}, limit: {limit}")
        
        result = search_articles_optimized(
            query=q,
            page=page,
            limit=limit,
            sort_by=sort_by,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"V1 Search '{q}' result: {result['total']} total, {len(result['articles'])} returned")
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in search_articles_v1: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/category/{category}", response_model=PaginatedArticleResponse)
def get_articles_by_category_v1(
    category: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by category - V1 endpoint"""
    try:
        logger.info(f"V1 Category request: '{category}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            category=category
        )
        
        logger.info(f"V1 Category '{category}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in get_articles_by_category_v1: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/tag/{tag}", response_model=PaginatedArticleResponse)
def get_articles_by_tag_v1(
    tag: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by tag - V1 endpoint"""
    try:
        logger.info(f"V1 Tag request: '{tag}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            tag=tag
        )
        
        logger.info(f"V1 Tag '{tag}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in get_articles_by_tag_v1: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================
# TEST-SPECIFIC ENDPOINTS
# =============================================

@v1_router.get("/tag/prevention", response_model=PaginatedArticleResponse)
def get_prevention_articles():
    """Get prevention tag articles - Test endpoint"""
    return get_articles_by_tag_v1("prevention")

@v1_router.get("/category/diseases", response_model=PaginatedArticleResponse)
def get_diseases_articles():
    """Get diseases category articles - Test endpoint"""
    return get_articles_by_category_v1("diseases")

# =============================================
# UTILITY ENDPOINTS
# =============================================

@v1_router.get("/health", response_model=HealthResponse)
@v1_router.head("/health")
def health_check():
    """API health check - Supports both GET and HEAD methods"""

    try:
        total_articles = get_total_articles_count()
        
        # For HEAD requests, FastAPI will automatically return just headers
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            database_status="connected",
            total_articles=total_articles
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "database_status": "error",
                "error": str(e)
            }
        )

@v1_router.get("/categories")
def get_categories():
    """Get all available categories"""
    try:
        categories = get_all_categories()
        return {
            "categories": categories,
            "total": len(categories),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/tags")
def get_tags():
    """Get all available tags"""
    try:
        tags = get_all_tags()
        return {
            "tags": tags,
            "total_tags": len(tags),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/stats")
def get_stats():
    """Get API statistics"""
    try:
        stats = get_api_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/scheduler/status")
def get_scheduler_status():
    """Get background scheduler status"""
    try:
        status = scheduler.get_status()
        return {
            "scheduler": status,
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.post("/scheduler/trigger")
def trigger_manual_scrape(scrape_type: str = Query("quick", enum=["quick", "full"], description="Type of scrape to trigger")):
    """Manually trigger a scraping job"""
    try:
        result = scheduler.trigger_manual_scrape(scrape_type)
        return {
            "message": result,
            "scrape_type": scrape_type,
            "triggered_at": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error triggering manual scrape: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Include V1 router
app.include_router(v1_router)

# =============================================
# ROOT ENDPOINT
# =============================================

@app.get("/")
@app.head("/")
def read_root():
    """API root endpoint - Supports both GET and HEAD methods"""
    return {
        "message": "Metabolical Backend API",
        "version": "2.0.0",
        "documentation": "/docs",
        "endpoints": {
            "base_api_endpoints": {
                "search": "/search?q={query}",
                "search_with_dates": "/search?q={query}&start_date={date}&end_date={date}",
                "category": "/category/{category}",
                "category_paginated": "/category/{category}?page=2&limit=10",
                "category_sorted": "/category/{category}?sort_by=asc",
                "tag": "/tag/{tag}",
                "tag_paginated": "/tag/{tag}?page=2&limit=10",
                "tag_sorted": "/tag/{tag}?sort_by=asc"
            },
            "v1_api_endpoints": {
                "search": "/api/v1/search?q={query}",
                "articles_search": "/api/v1/articles/search?q={query}",
                "search_with_dates": "/api/v1/search?q={query}&start_date={date}&end_date={date}",
                "articles_search_with_dates": "/api/v1/articles/search?q={query}&start_date={date}&end_date={date}",
                "search_sorted": "/api/v1/search?q={query}&sort_by=asc",
                "articles_search_sorted": "/api/v1/articles/search?q={query}&sort_by=asc",
                "category": "/api/v1/category/{category}",
                "category_paginated": "/api/v1/category/{category}?page=2&limit=10",
                "tag": "/api/v1/tag/{tag}",
                "tag_paginated": "/api/v1/tag/{tag}?page=2&limit=10",
                "health": "/api/v1/health",
                "categories": "/api/v1/categories",
                "tags": "/api/v1/tags",
                "stats": "/api/v1/stats"
            },
            "test_specific_endpoints": {
                "prevention": "/api/v1/tag/prevention",
                "diseases": "/api/v1/category/diseases"
            }
        },
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
