"""
Metabolical Backend API - Clean and Simplified
Health articles API with search, categorization, and pagination.
"""

from fastapi import FastAPI, HTTPException, Query, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict
import logging
from pathlib import Path
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import utilities
try:
    from .utils import *
    from .scheduler import health_scheduler
    from .config import config
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent))
    from utils import *
    from scheduler import health_scheduler
    from config import config

# FastAPI app
app = FastAPI(
    title="Metabolical Backend API",
    description="Health articles API with search, categorization, and pagination",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Startup and shutdown event handlers

import threading

def start_scheduler_in_thread():
    def run_scheduler():
        try:
            health_scheduler.start_scheduler()
            logger.info("✅ Background scheduler started successfully (threaded)")
        except Exception as e:
            logger.error(f"❌ Failed to start background scheduler (threaded): {e}")
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()

@app.on_event("startup")
async def startup_event():
    """Initialize the application and start background scheduler in a separate thread"""
    logger.info("🚀 Starting Metabolical Backend API...")
    
    # Clear all caches and refresh connections on startup to ensure fresh data
    try:
        clear_all_caches()
        force_refresh_connection()
        logger.info("🗑️ All caches cleared and connections refreshed on startup for fresh data")
    except Exception as e:
        logger.warning(f"⚠️ Could not clear caches on startup: {e}")
    
    # Check database initialization
    try:
        article_count = get_total_articles_count()
        logger.info(f"📊 Database initialized with {article_count} articles")
        if article_count == 0:
            logger.warning("⚠️ Database is empty - consider running database seeding")
    except Exception as e:
        logger.error(f"❌ Database initialization check failed: {e}")
        logger.info("🔧 Attempting to reinitialize database...")
        try:
            initialize_optimizations()
            logger.info("✅ Database reinitialized successfully")
        except Exception as reinit_error:
            logger.error(f"❌ Database reinitialization failed: {reinit_error}")
    # Start the background scheduler in a separate thread
    start_scheduler_in_thread()

@app.on_event("shutdown") 
async def shutdown_event():
    """Clean shutdown of the application"""
    logger.info("🛑 Shutting down Metabolical Backend API...")
    
    # Stop the background scheduler
    try:
        health_scheduler.stop_scheduler()
        logger.info("✅ Background scheduler stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error stopping background scheduler: {e}")

# Configure CORS based on environment
import os
from typing import List

def get_cors_origins() -> List[str]:
    """Get CORS origins based on environment"""
    # Check if CORS_ORIGINS environment variable is set
    cors_origins_env = os.getenv("CORS_ORIGINS")
    
    if cors_origins_env:
        # Parse comma-separated origins from environment variable
        origins = [origin.strip() for origin in cors_origins_env.split(",")]
        logger.info(f"Using CORS origins from environment: {origins}")
        return origins
    
    # Check for development environment - default to development if not explicitly in production
    is_development = (
        os.getenv("DEBUG", "true").lower() == "true" or 
        os.getenv("RENDER", "false").lower() == "false" or
        os.getenv("ENVIRONMENT", "development").lower() == "development"
    )
    
    if is_development:
        # Development CORS origins - allow most common development scenarios
        origins = [
            # Localhost variants
            "http://localhost:3000", "http://localhost:5173", "http://localhost:8080", "http://localhost:4200",
            "https://localhost:3000", "https://localhost:5173",
            "http://127.0.0.1:3000", "http://127.0.0.1:5173", "https://127.0.0.1:5173",
            "http://127.0.0.1:8000", "https://127.0.0.1:8000",
            
            # Your specific network IPs
            "http://192.168.1.153:5173", "http://192.168.1.145:8000",
            "https://192.168.1.153:5173", "https://192.168.1.145:8000",
            
            # Common local network patterns for development
            "http://192.168.1.1:5173", "http://192.168.1.2:5173", "http://192.168.1.100:5173",
            "http://192.168.1.101:5173", "http://192.168.1.102:5173", "http://192.168.1.150:5173",
            "http://192.168.1.151:5173", "http://192.168.1.152:5173", "http://192.168.1.154:5173",
            "http://192.168.0.1:5173", "http://192.168.0.100:5173", "http://192.168.0.101:5173",
            
            # Production domains
            "https://metabolical.in", "https://www.metabolical.in"
        ]
        
        logger.info(f"Development mode: Using permissive CORS origins - {len(origins)} origins allowed")
        return origins
    
    # Production CORS origins - allow your specific frontend domains and development IPs
    origins = [
        "https://metabolical.in",
        "https://www.metabolical.in",
        "http://127.0.0.1:5173",
        # "https://127.0.0.1:5173",
        # "http://localhost:5173",
        "https://localhost:5173",
        # Include local network IPs for development even in production mode
        "http://192.168.1.153:5173",
        "http://192.168.1.145:8000",
    ]
    
    logger.info(f"Production mode: Using restricted CORS origins: {origins}")
    return origins

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add middleware to ensure no-cache headers on all responses
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Add no-cache headers to all API responses
        if request.url.path.startswith("/api/") or request.url.path in ["/search", "/category", "/tag"]:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# Get CORS origins
cors_origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRFToken",
        "Cache-Control"
    ],
    expose_headers=["Content-Length", "X-Total-Count"],
    max_age=0,  # Disable preflight cache for fresh data
)

# Load categories on startup
try:
    CATEGORY_KEYWORDS = get_cached_category_keywords()
    CATEGORIES = list(CATEGORY_KEYWORDS.keys())
except Exception as e:
    logger.warning(f"Could not load categories: {e}")
    CATEGORIES = ["diseases", "news", "solutions", "food", "audience", "blogs_and_opinions", "international_health", "indian_health"]

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
    image_url: Optional[str] = None
    author: Optional[str] = None

class PaginatedArticleResponse(BaseModel):
    articles: List[ArticleSchema]
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_previous: bool
    last_updated: Optional[datetime] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database_status: str
    total_articles: Optional[int] = None

# Helper function to add no-cache headers
def add_no_cache_headers(response: Response):
    """Add headers to prevent caching of API responses"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Last-Modified"] = "0"
    response.headers["ETag"] = ""
    return response

# =============================================
# BASE API ENDPOINTS (NO PREFIX)
# =============================================

@app.get("/search", response_model=PaginatedArticleResponse)
def search_articles_base(
    response: Response,
    q: str = Query(..., description="Search query", min_length=2),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """Search articles - Base endpoint without prefix"""
    try:
        logger.info(f"🔍 Base Search: '{q}', page: {page}, limit: {limit}")
        
        result = search_articles_optimized(
            query=q,
            page=page,
            limit=limit,
            sort_by=sort_by,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"📊 Base Search '{q}' result: {result['total']} total, {len(result['articles'])} returned")
        
        # Add no-cache headers for fresh data
        add_no_cache_headers(response)
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in search_articles_base: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/category/{category}", response_model=PaginatedArticleResponse)
def get_articles_by_category_base(
    response: Response,
    category: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by category - Base endpoint without prefix"""
    try:
        logger.info(f"📂 Base Category request: '{category}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            category=category
        )
        
        logger.info(f"📊 Base Category '{category}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        # Add no-cache headers for fresh data
        add_no_cache_headers(response)
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in get_articles_by_category_base: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/tag/{tag}", response_model=PaginatedArticleResponse)
def get_articles_by_tag_base(
    response: Response,
    tag: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by tag - Base endpoint without prefix"""
    try:
        logger.info(f"🏷️ Base Tag request: '{tag}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            tag=tag
        )
        
        logger.info(f"📊 Base Tag '{tag}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        # Add no-cache headers for fresh data
        add_no_cache_headers(response)
        
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
            "search": "/api/v1/search",
            "articles_search": "/api/v1/articles/search", 
            "categories": "/api/v1/categories",
            "tags": "/api/v1/tags",
            "stats": "/api/v1/stats",
            "health": "/api/v1/health",
            "category_articles": "/api/v1/category/{category}",
            "tag_articles": "/api/v1/tag/{tag}"
        },
        "documentation": "/docs",
        "status": "active"
    }

@v1_router.get("/articles/search", response_model=PaginatedArticleResponse)
def search_articles_v1_articles(
    response: Response,
    q: str = Query(..., description="Search query", min_length=2),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """Search articles - V1 articles endpoint"""
    try:
        logger.info(f"🔍 V1 Articles Search: '{q}', page: {page}, limit: {limit}")
        
        result = search_articles_optimized(
            query=q,
            page=page,
            limit=limit,
            sort_by=sort_by,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"📊 V1 Articles Search '{q}' result: {result['total']} total, {len(result['articles'])} returned")
        
        # Add no-cache headers for fresh data
        add_no_cache_headers(response)
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in search_articles_v1_articles: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/search", response_model=PaginatedArticleResponse)
def search_articles_v1(
    response: Response,
    q: str = Query(..., description="Search query", min_length=2),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """Search articles - V1 endpoint"""
    try:
        logger.info(f"🔍 V1 Search: '{q}', page: {page}, limit: {limit}")
        
        result = search_articles_optimized(
            query=q,
            page=page,
            limit=limit,
            sort_by=sort_by,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"📊 V1 Search '{q}' result: {result['total']} total, {len(result['articles'])} returned")
        
        # Add no-cache headers for fresh data
        add_no_cache_headers(response)
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in search_articles_v1: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/category/{category}", response_model=PaginatedArticleResponse)
def get_articles_by_category_v1(
    response: Response,
    category: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by category - V1 endpoint"""
    try:
        logger.info(f"📂 V1 Category request: '{category}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            category=category
        )
        
        logger.info(f"📊 V1 Category '{category}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        # Add no-cache headers for fresh data
        add_no_cache_headers(response)
        
        return PaginatedArticleResponse(**result)
    except Exception as e:
        logger.error(f"Error in get_articles_by_category_v1: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@v1_router.get("/tag/{tag}", response_model=PaginatedArticleResponse)
def get_articles_by_tag_v1(
    response: Response,
    tag: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    sort_by: str = Query("desc", enum=["asc", "desc"], description="Sort order")
):
    """Get articles by tag - V1 endpoint"""
    try:
        logger.info(f"🏷️ V1 Tag request: '{tag}', page: {page}, limit: {limit}")
        
        result = get_articles_paginated_optimized(
            page=page,
            limit=limit,
            sort_by=sort_by,
            tag=tag
        )
        
        logger.info(f"📊 V1 Tag '{tag}' result: {result['total']} total articles, {len(result['articles'])} returned")
        
        # Add no-cache headers for fresh data
        add_no_cache_headers(response)
        
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
def health_check():
    """API health check"""
    try:
        total_articles = get_total_articles_count()
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

@v1_router.get("/debug/database")
def debug_database():
    """Database debug information for troubleshooting"""
    import os
    from pathlib import Path
    
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "database_path": DB_PATH,
        "database_exists": Path(DB_PATH).exists(),
        "database_size": 0,
        "database_readable": False,
        "database_writable": False,
        "parent_directory_exists": Path(DB_PATH).parent.exists(),
        "parent_directory_writable": False,
        "current_working_directory": os.getcwd(),
        "app_directory": str(Path(__file__).parent.parent),
        "user_permissions": {},
        "environment_vars": {},
        "connection_test": "not_attempted"
    }
    
    try:
        # Check database file
        db_path = Path(DB_PATH)
        if db_path.exists():
            debug_info["database_size"] = db_path.stat().st_size
            debug_info["database_readable"] = os.access(DB_PATH, os.R_OK)
            debug_info["database_writable"] = os.access(DB_PATH, os.W_OK)
        
        # Check parent directory
        parent_dir = db_path.parent
        if parent_dir.exists():
            debug_info["parent_directory_writable"] = os.access(parent_dir, os.W_OK)
        
        # User and process info
        debug_info["user_permissions"] = {
            "effective_user_id": os.geteuid() if hasattr(os, 'geteuid') else "N/A",
            "effective_group_id": os.getegid() if hasattr(os, 'getegid') else "N/A",
            "process_id": os.getpid()
        }
        
        # Environment variables
        debug_info["environment_vars"] = {
            "DATABASE_PATH": os.getenv("DATABASE_PATH"),
            "PYTHONPATH": os.getenv("PYTHONPATH"),
            "RENDER": os.getenv("RENDER"),
            "PORT": os.getenv("PORT")
        }
        
        # Test database connection
        try:
            with connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM articles")
                count = cursor.fetchone()[0]
                debug_info["connection_test"] = "success"
                debug_info["article_count"] = count
        except Exception as conn_error:
            debug_info["connection_test"] = f"failed: {str(conn_error)}"
            debug_info["article_count"] = 0
            
    except Exception as e:
        debug_info["error"] = str(e)
    
    return debug_info

@v1_router.get("/cors-info")
def get_cors_info():
    """Get CORS configuration information for debugging"""
    try:
        current_origins = get_cors_origins()
        cors_env = os.getenv("CORS_ORIGINS")
        is_development = os.getenv("DEBUG", "false").lower() == "true" or os.getenv("RENDER", "true").lower() == "false"
        
        return {
            "cors_origins": current_origins,
            "cors_origins_env": cors_env,
            "is_development": is_development,
            "debug_env": os.getenv("DEBUG"),
            "render_env": os.getenv("RENDER"),
            "environment_variables": {
                "DEBUG": os.getenv("DEBUG"),
                "RENDER": os.getenv("RENDER"),
                "CORS_ORIGINS": cors_env
            }
        }
    except Exception as e:
        logger.error(f"CORS info check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@v1_router.get("/scheduler/status")
def get_scheduler_status():
    """Get status of background scheduler - Cloud optimized"""
    try:
        jobs = health_scheduler.get_scheduled_jobs()
        
        # Get database stats for monitoring
        import sqlite3
        from pathlib import Path
        
        db_path = Path(__file__).parent.parent / "data" / "articles.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            # Get articles from last 24 hours
            cursor.execute("SELECT COUNT(*) FROM articles WHERE created_at >= datetime('now', '-1 day')")
            recent_articles = cursor.fetchone()[0]
            
            # Get latest article date
            cursor.execute("SELECT MAX(date) FROM articles")
            latest_article_date = cursor.fetchone()[0]
        
        return {
            "status": "running" if health_scheduler.is_running else "stopped",
            "timestamp": datetime.now().isoformat(),
            "cloud_environment": health_scheduler.is_cloud,
            "scheduled_jobs": jobs,
            "total_jobs": len(jobs),
            "database_stats": {
                "total_articles": total_articles,
                "articles_last_24h": recent_articles,
                "latest_article_date": latest_article_date
            },
            "next_scraping": next((j['next_run'] for j in jobs if j['id'] == 'health_scraper'), None),
            "last_keepalive": datetime.now().isoformat() if health_scheduler.is_cloud else None
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/scheduler/trigger")
async def trigger_scraper_manually():
    """Manually trigger the scraper - For testing and emergency updates"""
    try:
        logger.info("📞 Manual scraper trigger requested via API")
        result = await health_scheduler.run_scraper_now()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "message": "Scraper triggered successfully"
        }
    except Exception as e:
        logger.error(f"Error triggering manual scraper: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/scheduler/trigger-scraper")
async def trigger_scraper_manually():
    """Manually trigger the health news scraper"""
    try:
        logger.info("🚀 Manual scraper trigger requested via API")
        result = await health_scheduler.run_scraper_now()
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
    except Exception as e:
        logger.error(f"Error triggering scraper: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/cache/clear")
async def clear_application_cache():
    """Clear all application caches to ensure fresh data"""
    try:
        from .utils import clear_all_caches
        clear_all_caches()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "message": "All application caches cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing caches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.get("/config")
def get_api_config():
    """Get current API configuration"""
    try:
        from .config import config
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "configuration": config.get_config(),
            "filters": {
                "metabolic_filter_enabled": config.is_metabolic_filter_enabled(),
                "deduplication_enabled": config.is_deduplication_enabled()
            }
        }
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@v1_router.get("/metabolic-filter/status")
def get_metabolic_filter_status():
    """Get current metabolic filter status"""
    try:
        from .config import config
        from .metabolic_filter import metabolic_filter
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "metabolic_filter": {
                "enabled": config.is_metabolic_filter_enabled(),
                "threshold": config.METABOLIC_FILTER_THRESHOLD,
                "keyword_categories": len(metabolic_filter.metabolic_keywords),
                "total_keywords": sum(len(keywords) for keywords in metabolic_filter.metabolic_keywords.values())
            },
            "deduplication": {
                "enabled": config.is_deduplication_enabled(),
                "threshold": config.DEDUPLICATION_THRESHOLD
            }
        }
    except Exception as e:
        logger.error(f"Error getting metabolic filter status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@v1_router.post("/test-filter")
async def test_metabolic_filter():
    """Test the metabolic filter with sample data"""
    try:
        from .metabolic_filter import metabolic_filter, article_deduplicator
        
        # Sample test articles
        test_articles = [
            {
                "id": 1,
                "title": "New Study Links Diabetes to Heart Disease Risk",
                "summary": "Research shows strong connection between type 2 diabetes and cardiovascular complications.",
                "url": "https://example.com/diabetes-heart-study",
                "source": "Medical Journal",
                "category": "diseases",
                "tags": ["diabetes", "heart disease"]
            },
            {
                "id": 2,
                "title": "Celebrity Fashion Trends for Summer",
                "summary": "Latest fashion trends from Hollywood celebrities for the summer season.",
                "url": "https://example.com/fashion-trends",
                "source": "Fashion Magazine",
                "category": "lifestyle",
                "tags": ["fashion", "celebrities"]
            },
            {
                "id": 3,
                "title": "Metabolic Syndrome Prevention Through Diet",
                "summary": "How dietary changes can prevent metabolic syndrome and improve insulin sensitivity.",
                "url": "https://example.com/metabolic-syndrome-diet",
                "source": "Nutrition Research",
                "category": "nutrition",
                "tags": ["metabolic syndrome", "diet", "prevention"]
            },
            {
                "id": 4,
                "title": "Air Pollution Linked to Obesity Rates",
                "summary": "New research connects air pollution exposure to increased obesity and metabolic dysfunction.",
                "url": "https://example.com/pollution-obesity",
                "source": "Environmental Health",
                "category": "environmental",
                "tags": ["air pollution", "obesity", "environmental health"]
            }
        ]
        
        # Test metabolic filtering
        metabolic_results = []
        for article in test_articles:
            is_relevant, score, keywords = metabolic_filter.contains_metabolic_content(
                article['title'], article['summary'], ""
            )
            metabolic_results.append({
                "article_id": article['id'],
                "title": article['title'][:50] + "...",
                "is_metabolic_relevant": is_relevant,
                "relevance_score": round(score, 3),
                "matched_keywords": keywords[:5]  # Top 5 keywords
            })
        
        # Test filtering
        filtered_articles = metabolic_filter.filter_articles(test_articles.copy())
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "test_results": {
                "original_count": len(test_articles),
                "filtered_count": len(filtered_articles),
                "metabolic_analysis": metabolic_results,
                "filtered_article_ids": [article['id'] for article in filtered_articles]
            },
            "configuration": {
                "metabolic_filter_enabled": config.is_metabolic_filter_enabled(),
                "filter_threshold": config.METABOLIC_FILTER_THRESHOLD
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing metabolic filter: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
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

@v1_router.post("/clear-cache")
def clear_cache():
    """Clear all application caches and refresh connections for fresh data"""
    try:
        clear_all_caches()
        force_refresh_connection()
        return {
            "status": "success",
            "message": "All caches cleared and connections refreshed successfully",
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error clearing caches: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear caches")

# Include V1 router
app.include_router(v1_router)

# =============================================
# ROOT ENDPOINT
# =============================================

@app.get("/")
def read_root():
    """API root endpoint"""
    return {
        "message": "Metabolical Backend API",
        "version": "2.0.0",
        "documentation": "/docs",
        "endpoints": {
            "base": {
                "search": "/search?q={query}",
                "category": "/category/{category}",
                "tag": "/tag/{tag}"
            },
            "v1": {
                "search": "/api/v1/search?q={query}",
                "articles_search": "/api/v1/articles/search?q={query}",
                "category": "/api/v1/category/{category}",
                "tag": "/api/v1/tag/{tag}",
                "health": "/api/v1/health",
                "categories": "/api/v1/categories",
                "tags": "/api/v1/tags",
                "stats": "/api/v1/stats"
            },
            "test": {
                "prevention": "/api/v1/tag/prevention",
                "diseases": "/api/v1/category/diseases"
            }
        },
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
