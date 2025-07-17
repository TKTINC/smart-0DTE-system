#!/bin/bash

# Smart-0DTE-System One-Click Local Deployment Script
# This script automates the entire local deployment process

set -e  # Exit on any error

echo "🚀 Starting Smart-0DTE-System Local Deployment..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check prerequisites
print_status "Checking prerequisites..."

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

# Set up environment variables
print_status "Setting up environment variables..."

if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    cat > .env << EOF
# Smart-0DTE-System Environment Configuration

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/smart_0dte
REDIS_URL=redis://localhost:6379
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=smart-0dte-token-123456789
INFLUXDB_ORG=smart-0dte
INFLUXDB_BUCKET=market_data

# API Keys (Replace with your actual keys)
POLYGON_API_KEY=demo_key
ALPHA_VANTAGE_API_KEY=demo_key
OPENAI_API_KEY=demo_key

# IBKR Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
    print_warning "Created .env file with demo keys. Please update with your actual API keys."
else
    print_success ".env file already exists."
fi

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Clean up old volumes if requested
read -p "Do you want to clean up old data volumes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleaning up old volumes..."
    docker-compose down -v 2>/dev/null || true
    docker volume prune -f 2>/dev/null || true
fi

# Build and start services
print_status "Building and starting services..."
print_status "This may take several minutes on first run..."

# Use docker-compose or docker compose based on availability
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Build images
print_status "Building Docker images..."
$COMPOSE_CMD build --no-cache

# Start database services first
print_status "Starting database services..."
$COMPOSE_CMD up -d postgres redis influxdb

# Wait for databases to be ready
print_status "Waiting for databases to be ready..."
sleep 30

# Check database health
print_status "Checking database connectivity..."
for i in {1..30}; do
    if $COMPOSE_CMD exec -T postgres pg_isready -U postgres &>/dev/null; then
        print_success "PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "PostgreSQL failed to start within timeout"
        exit 1
    fi
    sleep 2
done

for i in {1..30}; do
    if $COMPOSE_CMD exec -T redis redis-cli ping &>/dev/null; then
        print_success "Redis is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Redis failed to start within timeout"
        exit 1
    fi
    sleep 2
done

# Initialize database
print_status "Initializing database schema..."
$COMPOSE_CMD exec -T postgres psql -U postgres -d smart_0dte -c "SELECT 1;" &>/dev/null || {
    print_status "Creating database..."
    $COMPOSE_CMD exec -T postgres createdb -U postgres smart_0dte 2>/dev/null || true
}

# Start application services
print_status "Starting application services..."
$COMPOSE_CMD up -d backend data-feed signal-generator

# Wait for backend to be ready
print_status "Waiting for backend service to be ready..."
for i in {1..60}; do
    if curl -f http://localhost:8000/health &>/dev/null; then
        print_success "Backend service is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        print_error "Backend service failed to start within timeout"
        exit 1
    fi
    sleep 5
done

# Start frontend
print_status "Starting frontend service..."
$COMPOSE_CMD up -d frontend

# Wait for frontend to be ready
print_status "Waiting for frontend service to be ready..."
sleep 30

# Final health check
print_status "Performing final health check..."
if curl -f http://localhost:8000/health &>/dev/null; then
    print_success "Backend health check passed!"
else
    print_error "Backend health check failed!"
    exit 1
fi

if curl -f http://localhost:3000 &>/dev/null; then
    print_success "Frontend health check passed!"
else
    print_warning "Frontend may still be starting up..."
fi

# Display deployment summary
echo ""
echo "🎉 Smart-0DTE-System Deployment Complete!"
echo "=========================================="
echo ""
echo "📊 Service URLs:"
echo "   Frontend:     http://localhost:3000"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   InfluxDB UI:  http://localhost:8086"
echo ""
echo "🔧 Database Connections:"
echo "   PostgreSQL:   localhost:5432 (user: postgres, db: smart_0dte)"
echo "   Redis:        localhost:6379"
echo "   InfluxDB:     localhost:8086 (org: smart-0dte, bucket: market_data)"
echo ""
echo "📝 Next Steps:"
echo "   1. Update API keys in .env file"
echo "   2. Configure IBKR connection settings"
echo "   3. Access the frontend at http://localhost:3000"
echo "   4. Check logs with: $COMPOSE_CMD logs -f [service_name]"
echo ""
echo "🛑 To stop all services: $COMPOSE_CMD down"
echo "🔄 To restart services: $COMPOSE_CMD restart"
echo "📋 To view logs: $COMPOSE_CMD logs -f"
echo ""
print_success "Deployment completed successfully!"

