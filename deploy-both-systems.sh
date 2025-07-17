#!/bin/bash

# Unified One-Click Deployment Script for Both Systems
# This script deploys both Smart-0DTE-System and Mag7-7DTE-System

set -e  # Exit on any error

echo "🚀 Starting Unified Deployment of Both Trading Systems..."
echo "========================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_system() {
    echo -e "${PURPLE}[SYSTEM]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites for both systems..."

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

print_success "Prerequisites check passed!"

# Determine compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Function to deploy a system
deploy_system() {
    local system_name=$1
    local system_dir=$2
    local frontend_port=$3
    local backend_port=$4
    
    print_system "Deploying $system_name..."
    
    cd "$system_dir"
    
    # Stop any existing containers
    print_status "Stopping existing $system_name containers..."
    $COMPOSE_CMD down --remove-orphans 2>/dev/null || true
    
    # Build and start services
    print_status "Building $system_name Docker images..."
    $COMPOSE_CMD build --no-cache
    
    # Start database services first
    print_status "Starting $system_name database services..."
    $COMPOSE_CMD up -d postgres redis influxdb
    
    # Wait for databases
    print_status "Waiting for $system_name databases to be ready..."
    sleep 20
    
    # Start application services
    print_status "Starting $system_name application services..."
    $COMPOSE_CMD up -d backend data-feed signal-generator
    
    # Wait for backend
    print_status "Waiting for $system_name backend to be ready..."
    for i in {1..30}; do
        if curl -f "http://localhost:$backend_port/health" &>/dev/null; then
            print_success "$system_name backend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "$system_name backend failed to start"
            return 1
        fi
        sleep 5
    done
    
    # Start frontend
    print_status "Starting $system_name frontend..."
    $COMPOSE_CMD up -d frontend
    
    print_success "$system_name deployment completed!"
    
    cd - > /dev/null
}

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# System paths
SMART_0DTE_DIR="$BASE_DIR/smart-0DTE-system"
MAG7_7DTE_DIR="$BASE_DIR/mag7-7DTE-system"

# Check if both system directories exist
if [ ! -d "$SMART_0DTE_DIR" ]; then
    print_error "Smart-0DTE-System directory not found at $SMART_0DTE_DIR"
    exit 1
fi

if [ ! -d "$MAG7_7DTE_DIR" ]; then
    print_error "Mag7-7DTE-System directory not found at $MAG7_7DTE_DIR"
    exit 1
fi

# Ask user which systems to deploy
echo ""
echo "Which systems would you like to deploy?"
echo "1) Smart-0DTE-System only"
echo "2) Mag7-7DTE-System only"
echo "3) Both systems"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        print_system "Deploying Smart-0DTE-System only..."
        deploy_system "Smart-0DTE-System" "$SMART_0DTE_DIR" 3000 8000
        ;;
    2)
        print_system "Deploying Mag7-7DTE-System only..."
        deploy_system "Mag7-7DTE-System" "$MAG7_7DTE_DIR" 3001 8001
        ;;
    3)
        print_system "Deploying both systems..."
        
        # Deploy Smart-0DTE-System first
        deploy_system "Smart-0DTE-System" "$SMART_0DTE_DIR" 3000 8000
        
        # Wait a bit between deployments
        sleep 10
        
        # Deploy Mag7-7DTE-System
        deploy_system "Mag7-7DTE-System" "$MAG7_7DTE_DIR" 3001 8001
        ;;
    *)
        print_error "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Final health checks and summary
echo ""
echo "🎉 Deployment Summary"
echo "===================="

if [ "$choice" = "1" ] || [ "$choice" = "3" ]; then
    echo ""
    print_system "Smart-0DTE-System (0-Day-To-Expiration ETF Options):"
    echo "   Frontend:     http://localhost:3000"
    echo "   Backend API:  http://localhost:8000"
    echo "   API Docs:     http://localhost:8000/docs"
    echo "   InfluxDB UI:  http://localhost:8086"
    echo "   Database:     PostgreSQL on port 5432"
    echo "   Redis:        Port 6379"
fi

if [ "$choice" = "2" ] || [ "$choice" = "3" ]; then
    echo ""
    print_system "Mag7-7DTE-System (7-Day-To-Expiration Magnificent 7 Stocks):"
    echo "   Frontend:     http://localhost:3001"
    echo "   Backend API:  http://localhost:8001"
    echo "   API Docs:     http://localhost:8001/docs"
    echo "   InfluxDB UI:  http://localhost:8087"
    echo "   Database:     PostgreSQL on port 5433"
    echo "   Redis:        Port 6380"
fi

echo ""
echo "📝 Important Notes:"
echo "   • Update API keys in each system's .env file"
echo "   • Configure IBKR connection settings"
echo "   • Both systems can run simultaneously on different ports"
echo "   • Use 'docker-compose logs -f' in each directory to view logs"
echo ""
echo "🛑 To stop systems:"
echo "   • Smart-0DTE: cd $SMART_0DTE_DIR && docker-compose down"
echo "   • Mag7-7DTE:  cd $MAG7_7DTE_DIR && docker-compose down"
echo ""
print_success "All selected systems deployed successfully!"

