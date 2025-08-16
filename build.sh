#!/bin/bash
# Build script for deployment

echo "🔧 Installing Python dependencies..."
pip install --upgrade pip

# Use production requirements if available, otherwise fall back to main requirements
if [ -f "requirements-prod.txt" ]; then
    echo "📦 Using production requirements..."
    pip install -r requirements-prod.txt
else
    echo "� Using main requirements..."
    pip install -r requirements.txt
fi

echo "�📁 Creating required directories..."
mkdir -p data

echo "🗄️ Database setup..."
echo "   Database will be created automatically by the application"

echo "🔧 Setting up application..."
# Ensure proper permissions
chmod +x start.py

echo "✅ Build completed successfully!"
echo "🚀 Ready to start with: python start.py"
echo "📱 Health check available at: /api/v1/health"
