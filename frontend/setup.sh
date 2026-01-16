#!/bin/bash

echo "🎬 TranscriptorIO Frontend - Setup Script"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo ""
    echo "Please install Node.js 18+ using one of these methods:"
    echo ""
    echo "Method 1: Using nvm (recommended)"
    echo "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    echo "  source ~/.bashrc  # or ~/.zshrc"
    echo "  nvm install 18"
    echo "  nvm use 18"
    echo ""
    echo "Method 2: Using package manager"
    echo "  Ubuntu/Debian: sudo apt install nodejs npm"
    echo "  Fedora: sudo dnf install nodejs npm"
    echo "  Arch: sudo pacman -S nodejs npm"
    echo ""
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js detected: $NODE_VERSION"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo "✅ npm detected: v$NPM_VERSION"
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ package.json not found. Are you in the frontend directory?"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
echo ""
npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencies installed successfully!"
    echo ""
    echo "=========================================="
    echo "🚀 Next Steps"
    echo "=========================================="
    echo ""
    echo "1. Make sure the backend is running:"
    echo "   cd ../backend"
    echo "   python cli.py server"
    echo ""
    echo "2. Start the frontend dev server:"
    echo "   cd frontend"
    echo "   npm run dev"
    echo ""
    echo "3. Open your browser:"
    echo "   http://localhost:3000"
    echo ""
    echo "=========================================="
else
    echo ""
    echo "❌ Failed to install dependencies"
    exit 1
fi

