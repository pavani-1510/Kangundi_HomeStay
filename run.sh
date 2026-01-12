#!/bin/bash

# Flask Auth Application Setup and Run Script

echo "🚀 Setting up Flask Auth Application..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Run the application
echo "✅ Starting Flask application..."
echo "🌐 Application will be available at: http://localhost:5000"
echo "📝 Press Ctrl+C to stop the server"
echo ""

python app.py
