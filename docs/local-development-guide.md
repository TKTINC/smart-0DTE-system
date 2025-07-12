# Smart-0DTE-System Local Development Guide

This guide provides comprehensive instructions for setting up, developing, and testing the Smart-0DTE-System locally.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Backend Development](#backend-development)
5. [Frontend Development](#frontend-development)
6. [Testing](#testing)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Python**: 3.11 or higher
- **Node.js**: 20.x or higher
- **Docker**: 20.10 or higher (optional but recommended)
- **Git**: Latest version
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **Storage**: At least 10GB free space

### Required Accounts and API Keys

1. **Databento Account**: For real-time market data
   - Sign up at [databento.com](https://databento.com)
   - Obtain API key from dashboard

2. **Interactive Brokers Account**: For trading
   - Open account at [interactivebrokers.com](https://interactivebrokers.com)
   - Install TWS or IB Gateway
   - Enable API access in account settings

3. **AWS Account** (for cloud deployment):
   - Create account at [aws.amazon.com](https://aws.amazon.com)
   - Configure IAM user with appropriate permissions

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/TKTINC/smart-0DTE-system.git
cd smart-0DTE-system
```

### 2. Create Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/smart_0dte_db
REDIS_URL=redis://localhost:6379/0
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=smart_0dte_bucket

# Market Data Configuration
DATABENTO_API_KEY=your_databento_api_key
DATABENTO_DATASET=XNAS.ITCH
MOCK_DATA_MODE=true  # Set to false for live data

# Trading Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1
PAPER_TRADING=true  # Set to false for live trading

# System Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here

# Risk Management
MAX_DAILY_LOSS=1000.0
MAX_POSITION_SIZE=5000.0
MAX_POSITIONS_PER_SYMBOL=3
VIX_THRESHOLD=30.0
CONFIDENCE_THRESHOLD=0.65

# AI/ML Configuration
MODEL_RETRAIN_INTERVAL=7  # days
FEATURE_STORE_ENABLED=true
```

### 3. Install System Dependencies

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm postgresql redis-server
```

#### macOS:
```bash
brew install python@3.11 node postgresql redis
```

#### Windows (WSL2):
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm postgresql redis-server
```

## Database Setup

### 1. PostgreSQL Setup

#### Start PostgreSQL service:
```bash
# Ubuntu/Debian
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS
brew services start postgresql
```

#### Create database and user:
```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE smart_0dte_db;
CREATE USER smart_0dte_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE smart_0dte_db TO smart_0dte_user;
\q
```

### 2. Redis Setup

#### Start Redis service:
```bash
# Ubuntu/Debian
sudo systemctl start redis-server
sudo systemctl enable redis-server

# macOS
brew services start redis
```

#### Test Redis connection:
```bash
redis-cli ping
# Should return: PONG
```

### 3. InfluxDB Setup (Optional)

#### Using Docker:
```bash
docker run -d \
  --name influxdb \
  -p 8086:8086 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=password123 \
  -e DOCKER_INFLUXDB_INIT_ORG=smart-0dte \
  -e DOCKER_INFLUXDB_INIT_BUCKET=market_data \
  influxdb:2.7
```

## Backend Development

### 1. Python Environment Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Migration

```bash
# Initialize database schema
python -c "
from app.core.database import create_tables
import asyncio
asyncio.run(create_tables())
"
```

### 3. Start Backend Services

#### Development Mode:
```bash
# Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the development script
python scripts/start_dev.py
```

#### Production Mode:
```bash
# Start with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 4. Verify Backend Setup

Test the API endpoints:

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## Frontend Development

### 1. Frontend Setup

```bash
cd smart-0dte-frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Or with specific host
npm run dev -- --host 0.0.0.0
```

### 2. Environment Configuration

Create `smart-0dte-frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=development
```

### 3. Verify Frontend Setup

Open your browser and navigate to:
- Development: `http://localhost:5173`
- Production build: `npm run build && npm run preview`

## Testing

### 1. Backend Testing

```bash
cd backend

# Run all tests
python tests/run_tests.py all

# Run specific test types
python tests/run_tests.py unit
python tests/run_tests.py integration
python tests/run_tests.py e2e

# Run with coverage
python tests/run_tests.py all --coverage

# Run specific test file
python tests/run_tests.py --specific tests/unit/services/test_intelligence_service.py

# Generate test report
python tests/run_tests.py --report
```

### 2. Frontend Testing

```bash
cd smart-0dte-frontend

# Run unit tests
npm test

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

### 3. Integration Testing

```bash
# Start all services
docker-compose up -d

# Run integration tests
cd backend
python tests/run_tests.py integration

# Run E2E tests
python tests/run_tests.py e2e
```

## Development Workflow

### 1. Daily Development Routine

```bash
# 1. Update repository
git pull origin main

# 2. Activate backend environment
cd backend && source venv/bin/activate

# 3. Install any new dependencies
pip install -r requirements.txt

# 4. Run tests
python tests/run_tests.py unit

# 5. Start development servers
# Terminal 1: Backend
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd ../smart-0dte-frontend && npm run dev

# Terminal 3: Redis (if not running as service)
redis-server

# Terminal 4: PostgreSQL (if not running as service)
postgres -D /usr/local/var/postgres
```

### 2. Code Quality Checks

```bash
# Backend code formatting
cd backend
black app/ tests/
isort app/ tests/
flake8 app/ tests/

# Frontend code formatting
cd smart-0dte-frontend
npm run lint
npm run format
```

### 3. Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new feature description"

# Run tests before pushing
cd backend && python tests/run_tests.py all

# Push changes
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### 4. Database Development

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Reset database (development only)
python scripts/reset_database.py
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Issues

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Check connection
psql -h localhost -U smart_0dte_user -d smart_0dte_db
```

#### 2. Redis Connection Issues

**Problem**: `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`

**Solution**:
```bash
# Check Redis status
redis-cli ping

# Start Redis
sudo systemctl start redis-server

# Check Redis logs
sudo journalctl -u redis-server
```

#### 3. Python Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Ensure you're in the backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 4. Frontend Build Issues

**Problem**: `npm ERR! peer dep missing`

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall dependencies
npm install
```

#### 5. API Connection Issues

**Problem**: Frontend cannot connect to backend API

**Solution**:
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS configuration in backend
# Verify VITE_API_BASE_URL in frontend .env.local

# Check firewall settings
sudo ufw status
```

### 6. Performance Issues

**Problem**: Slow API responses or high memory usage

**Solution**:
```bash
# Monitor system resources
htop

# Check database performance
# In PostgreSQL:
SELECT * FROM pg_stat_activity;

# Check Redis memory usage
redis-cli info memory

# Profile Python application
python -m cProfile -o profile.stats app/main.py
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
CREATE INDEX idx_signals_timestamp ON signals(timestamp);
CREATE INDEX idx_trades_symbol_timestamp ON trades(symbol, timestamp);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM market_data WHERE symbol = 'SPY' AND timestamp > NOW() - INTERVAL '1 hour';
```

### 2. Redis Optimization

```bash
# Configure Redis for optimal performance
# Edit /etc/redis/redis.conf

# Set appropriate memory limit
maxmemory 2gb
maxmemory-policy allkeys-lru

# Enable persistence if needed
save 900 1
save 300 10
save 60 10000
```

### 3. Application Optimization

```python
# Use connection pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# Implement caching
from functools import lru_cache

@lru_cache(maxsize=1000)
def expensive_calculation(param):
    # Expensive operation
    return result
```

### 4. Frontend Optimization

```javascript
// Use React.memo for expensive components
const ExpensiveComponent = React.memo(({ data }) => {
  return <div>{/* Expensive rendering */}</div>;
});

// Implement virtual scrolling for large lists
import { FixedSizeList as List } from 'react-window';

// Use code splitting
const LazyComponent = React.lazy(() => import('./LazyComponent'));
```

## Development Tools

### 1. Recommended VS Code Extensions

- Python
- Pylance
- Black Formatter
- ES7+ React/Redux/React-Native snippets
- Prettier - Code formatter
- GitLens
- Docker
- PostgreSQL

### 2. Debugging Setup

#### Backend Debugging:
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/app/main.py",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      }
    }
  ]
}
```

#### Frontend Debugging:
```json
// .vscode/launch.json
{
  "name": "Launch Chrome",
  "request": "launch",
  "type": "chrome",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/smart-0dte-frontend/src"
}
```

### 3. Monitoring and Logging

```python
# Configure structured logging
import structlog

logger = structlog.get_logger()

# Use in your code
logger.info("Processing signal", symbol="SPY", confidence=0.85)
```

## Security Considerations

### 1. Environment Variables

```bash
# Never commit .env files
echo ".env" >> .gitignore

# Use strong secrets
openssl rand -hex 32  # Generate secret key
```

### 2. API Security

```python
# Implement rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/data")
@limiter.limit("100/minute")
async def get_data(request: Request):
    return {"data": "value"}
```

### 3. Database Security

```sql
-- Create read-only user for reporting
CREATE USER readonly_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE smart_0dte_db TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

## Next Steps

1. **Read the API Documentation**: Visit `/docs` endpoint for interactive API documentation
2. **Explore the Codebase**: Start with `app/main.py` and follow the imports
3. **Run the Test Suite**: Ensure all tests pass before making changes
4. **Set Up Your IDE**: Configure debugging and code formatting
5. **Join the Development Community**: Contribute to the project on GitHub

## Support

For development support:
- Check the [GitHub Issues](https://github.com/TKTINC/smart-0DTE-system/issues)
- Review the [API Documentation](http://localhost:8000/docs)
- Read the [System Architecture](./system-architecture.md)

Happy coding! 🚀

