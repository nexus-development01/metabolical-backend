# 🏥 Metabolical Backend API

A FastAPI-based backend service for health articles with intelligent search, categorization, and real-time scraping capabilities. Built with performance and scalability in mind.

## ✨ Features

- 🔍 **Advanced Search**: Full-text search across articles with intelligent ranking
- 📂 **Smart Categorization**: Automated categorization into health domains
- 🕷️ **Multi-Source Scraping**: Aggregates content from multiple health news sources
- ⚡ **High Performance**: SQLite with connection pooling and in-memory caching
- 📄 **Pagination**: Efficient pagination for large datasets
- 🌐 **CORS Enabled**: Ready for frontend integration
- 📊 **RESTful API**: Clean, documented endpoints following REST principles
- 🔧 **Easy Deployment**: Simple scripts for local development and production

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd metabolical-backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**
   
   **Local Development:**
   ```bash
   python start.py --port 8000
   ```
   
   **With Debug Mode:**
   ```bash
   python start.py --debug --port 8000
   ```
   
   **Production Deployment:**
   ```bash
   python start.py --port 80 --public-url https://metabolical.in
   ```

4. **Access the API**
   - **Local**: http://localhost:8000
   - **Swagger Docs**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc

5. **Stop the server**
   ```bash
   python stop.py
   ```

## 📁 Project Structure

```
metabolical-backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── utils.py               # Utility functions
│   ├── url_validator.py       # URL validation logic
│   └── __init__.py
├── config/
│   ├── health_categories.yml  # Category definitions
│   ├── scraper_config.py     # Scraper configurations
│   └── __init__.py
├── data/
│   └── articles.db           # SQLite database
├── scrapers/
│   ├── comprehensive_news_scraper.py
│   ├── python313_compatible_scraper.py
│   ├── simple_health_scraper.py
│   ├── smart_news_aggregator.py
│   ├── social_media_scraper.py
│   └── __init__.py
├── docs/
│   ├── ALL_ENDPOINTS.md
│   ├── Endpoint.md
│   ├── PERFORMANCE_IMPROVEMENTS.md
│   ├── SEARCH_ENDPOINTS.md
│   └── SMARTNEWS_AGGREGATION.md
├── start.py                  # Server startup script
├── stop.py                   # Server shutdown script
├── requirements.txt          # Python dependencies
└── README.md
```

## 📋 API Endpoints

All endpoints use the `/api/v1` prefix:

### Core Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check endpoint |
| GET | `/api/v1/stats` | API statistics and metrics |

### Articles
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/articles/` | Get all articles with pagination |
| GET | `/api/v1/articles/latest` | Get latest articles |
| GET | `/api/v1/articles/search?q={query}` | Search articles by query |
| GET | `/api/v1/articles/{category}` | Get articles by category |
| GET | `/api/v1/articles/{category}/{subcategory}` | Get articles by category and subcategory |

### Categories & Legacy
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/categories` | Get all available categories |
| GET | `/api/v1/search?q={query}` | Legacy search endpoint |

## 🔍 Usage Examples

### Search for Articles
```bash
# Search for diabetes-related articles
curl "https://metabolical.in/api/v1/articles/search?q=diabetes&limit=10"

# Get articles from diseases category
curl "https://metabolical.in/api/v1/articles/diseases?page=1&limit=20"

# Get latest articles
curl "https://metabolical.in/api/v1/articles/latest?limit=5"
```

### Sample Response
```json
{
  "articles": [
    {
      "id": 123,
      "title": "Understanding Diabetes: A Comprehensive Guide",
      "summary": "Learn about diabetes types, symptoms, and management strategies...",
      "url": "https://healthsource.com/diabetes-guide",
      "source": "Health News Daily",
      "date": "2025-07-30T10:00:00Z",
      "category": "diseases",
      "subcategory": "diabetes",
      "tags": ["health", "diabetes", "blood-sugar", "management"]
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

## 📊 Available Categories

- **diseases** - Medical conditions and disorders
- **news** - Latest health news and updates
- **solutions** - Treatment options and remedies
- **food** - Nutrition and dietary information
- **audience** - Targeted health advice for specific groups
- **blogs_and_opinions** - Expert opinions and personal experiences

## ⚙️ Configuration

### Environment Variables
Create a `.env` file for production deployment:
```env
PORT=80
PUBLIC_URL=https://metabolical.in
DEBUG=false
```

### Category Configuration
Edit `config/health_categories.yml` to customize article categorization:
```yaml
diseases:
  - diabetes
  - hypertension
  - cancer
news:
  - breaking
  - research
  - updates
```

## 🔧 Development

### Running Tests
```bash
# Health check
curl "http://localhost:8000/api/v1/health"

# Get statistics
curl "http://localhost:8000/api/v1/stats"
```

### Debug Mode
Enable detailed logging:
```bash
python start.py --debug --port 8000
```

### Adding New Scrapers
1. Create a new scraper in `scrapers/` directory
2. Follow the existing scraper patterns
3. Update `scraper_config.py` to include the new scraper

## 📈 Performance Features

- **SQLite Connection Pooling**: Optimized database connections
- **Indexed Fields**: Fast query performance on searchable fields
- **In-Memory Caching**: Frequently accessed data cached for speed
- **Gzip Compression**: Reduced response payload sizes
- **Paginated Responses**: Efficient handling of large datasets
- **Asynchronous Processing**: Non-blocking request handling

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `articles.db missing` | Check if `data/` directory exists and is writable |
| Port conflict | Use `python stop.py` or change port number |
| Dependency errors | Run `pip install -r requirements.txt` |
| Scraper failures | Check `scraper_config.py` and network connectivity |

### Logs & Debugging
- Run with `--debug` flag for detailed logs
- Check console output for error messages
- Monitor API response times and error rates

## 🚀 Deployment

### Production Deployment
```bash
# Set environment variables
export PORT=80
export PUBLIC_URL=https://metabolical.in

# Start the server
python start.py --port 80 --public-url https://metabolical.in
```

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "start.py", "--port", "8000"]
```

## 📚 Documentation

For detailed API documentation, visit:
- [All Endpoints](docs/ALL_ENDPOINTS.md)
- [Search Endpoints](docs/SEARCH_ENDPOINTS.md)
- [Performance Improvements](docs/PERFORMANCE_IMPROVEMENTS.md)
- [Smart News Aggregation](docs/SMARTNEWS_AGGREGATION.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation in the `docs/` folder
- Review the troubleshooting section above

---

**Metabolical API** - Delivering clean, scalable health article aggregation with intelligent categorization and lightning-fast search capabilities.
