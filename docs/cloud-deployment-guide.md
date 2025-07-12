# Smart-0DTE-System Cloud Deployment Guide

**Version:** 1.0  
**Date:** December 7, 2025  
**Author:** Manus AI  

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Domain and SSL Certificate Setup](#domain-and-ssl-certificate-setup)
4. [Environment Configuration](#environment-configuration)
5. [Infrastructure Deployment](#infrastructure-deployment)
6. [Application Deployment](#application-deployment)
7. [Database Setup and Migration](#database-setup-and-migration)
8. [Monitoring and Logging Setup](#monitoring-and-logging-setup)
9. [Security Configuration](#security-configuration)
10. [Testing and Validation](#testing-and-validation)
11. [Production Checklist](#production-checklist)
12. [Troubleshooting](#troubleshooting)
13. [Maintenance and Updates](#maintenance-and-updates)

## Prerequisites

### Required Tools and Accounts

Before beginning the cloud deployment process, ensure you have the following tools installed and accounts configured on your local machine.

**AWS CLI Installation:**
```bash
# Install AWS CLI v2 (macOS)
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Install AWS CLI v2 (Linux)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install AWS CLI v2 (Windows)
# Download and run: https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify installation
aws --version
```

**Docker Installation:**
```bash
# Install Docker (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER

# Install Docker (macOS)
# Download Docker Desktop from: https://www.docker.com/products/docker-desktop

# Install Docker (Windows)
# Download Docker Desktop from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

**Node.js and npm:**
```bash
# Install Node.js 18+ (using nvm - recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18

# Verify installation
node --version
npm --version
```

### Required Accounts and Services

**AWS Account Requirements:**
- Active AWS account with billing enabled
- IAM user with programmatic access and appropriate permissions
- AWS CLI configured with credentials
- Sufficient service limits for ECS, RDS, ElastiCache, and other services

**Third-Party Service Accounts:**
- Interactive Brokers account with API access enabled
- Databento account with real-time data subscription
- Domain registrar account (for custom domain setup)

**Minimum AWS Permissions Required:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "ec2:*",
                "ecs:*",
                "rds:*",
                "elasticache:*",
                "elasticloadbalancing:*",
                "cloudfront:*",
                "route53:*",
                "acm:*",
                "secretsmanager:*",
                "logs:*",
                "cloudwatch:*",
                "iam:*",
                "s3:*",
                "ecr:*"
            ],
            "Resource": "*"
        }
    ]
}
```

## AWS Account Setup

### Initial AWS Configuration

Configure your AWS CLI with the appropriate credentials and region settings for optimal performance and compliance with your requirements.

**Configure AWS CLI:**
```bash
# Configure AWS credentials
aws configure

# Enter the following when prompted:
# AWS Access Key ID: [Your IAM user access key]
# AWS Secret Access Key: [Your IAM user secret key]
# Default region name: us-east-1 (recommended for global services)
# Default output format: json

# Verify configuration
aws sts get-caller-identity
aws ec2 describe-regions --output table
```

**Set Environment Variables:**
```bash
# Add to your ~/.bashrc or ~/.zshrc
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export PROJECT_NAME=smart-0dte-system

# Reload shell configuration
source ~/.bashrc  # or source ~/.zshrc
```

### Service Limit Verification

Verify that your AWS account has sufficient service limits for the Smart-0DTE-System deployment. The system requires multiple AWS services with specific capacity requirements.

**Check Current Limits:**
```bash
# Check ECS limits
aws ecs describe-account-attributes

# Check RDS limits
aws rds describe-account-attributes

# Check ElastiCache limits
aws elasticache describe-cache-clusters

# Check VPC limits
aws ec2 describe-account-attributes --attribute-names supported-platforms
```

**Request Limit Increases (if needed):**
- ECS Tasks: Minimum 50 tasks per service
- RDS Instances: Minimum 5 instances
- ElastiCache Nodes: Minimum 6 nodes
- VPC: Minimum 5 VPCs per region
- Elastic Load Balancers: Minimum 10 ALBs

## Domain and SSL Certificate Setup

### Domain Configuration

Setting up a custom domain provides professional branding and enables SSL certificate configuration for secure communications.

**Purchase and Configure Domain:**
```bash
# If using Route 53 for domain registration
aws route53domains register-domain \
    --domain-name your-domain.com \
    --duration-in-years 1 \
    --admin-contact file://admin-contact.json \
    --registrant-contact file://registrant-contact.json \
    --tech-contact file://tech-contact.json

# Create hosted zone
aws route53 create-hosted-zone \
    --name your-domain.com \
    --caller-reference $(date +%s)
```

**Create Contact Information File (admin-contact.json):**
```json
{
    "FirstName": "Your",
    "LastName": "Name",
    "ContactType": "PERSON",
    "OrganizationName": "Your Organization",
    "AddressLine1": "123 Main Street",
    "City": "Your City",
    "State": "Your State",
    "CountryCode": "US",
    "ZipCode": "12345",
    "PhoneNumber": "+1.5551234567",
    "Email": "admin@your-domain.com"
}
```

### SSL Certificate Setup

SSL certificates are essential for secure HTTPS communications and are required for production deployment.

**Request SSL Certificate:**
```bash
# Request certificate for your domain
aws acm request-certificate \
    --domain-name your-domain.com \
    --subject-alternative-names "*.your-domain.com" \
    --validation-method DNS \
    --region us-east-1

# Get certificate ARN (save this for deployment)
aws acm list-certificates \
    --certificate-statuses ISSUED \
    --query 'CertificateSummaryList[0].CertificateArn' \
    --output text
```

**Validate Certificate:**
```bash
# Get validation records
aws acm describe-certificate \
    --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012 \
    --query 'Certificate.DomainValidationOptions'

# Add CNAME records to your DNS (Route 53 or external provider)
# The validation process typically takes 5-30 minutes
```

## Environment Configuration

### Environment Variables Setup

Create comprehensive environment configuration files for different deployment stages (development, staging, production).

**Create Production Environment File (.env.production):**
```bash
# Navigate to project directory
cd smart-0DTE-system

# Create production environment file
cat > .env.production << 'EOF'
# Environment
NODE_ENV=production
ENVIRONMENT=production

# Database Configuration
DATABASE_URL=postgresql://username:password@rds-endpoint:5432/smart_0dte_prod
DATABASE_HOST=your-rds-endpoint.region.rds.amazonaws.com
DATABASE_PORT=5432
DATABASE_NAME=smart_0dte_prod
DATABASE_USER=smart0dte_user
DATABASE_PASSWORD=your-secure-password

# Redis Configuration
REDIS_URL=redis://your-elasticache-endpoint:6379
REDIS_HOST=your-elasticache-endpoint.cache.amazonaws.com
REDIS_PORT=6379

# InfluxDB Configuration
INFLUXDB_URL=http://your-influxdb-endpoint:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=smart-0dte-system
INFLUXDB_BUCKET=market-data

# API Keys and Secrets
DATABENTO_API_KEY=your-databento-api-key
IBKR_CLIENT_ID=your-ibkr-client-id
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_PAPER_TRADING=false

# JWT and Security
JWT_SECRET=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
SECRET_KEY=your-application-secret-key

# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=smart-0dte-system-storage
AWS_CLOUDFRONT_DOMAIN=your-cloudfront-domain.cloudfront.net

# Application Configuration
API_V1_STR=/api/v1
PROJECT_NAME=Smart-0DTE-System
VERSION=1.0.0
DEBUG=false

# CORS Configuration
BACKEND_CORS_ORIGINS=["https://your-domain.com","https://www.your-domain.com"]

# Monitoring and Logging
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn
DATADOG_API_KEY=your-datadog-api-key

# Trading Configuration
MAX_POSITIONS_PER_SYMBOL=3
MAX_TOTAL_POSITIONS=10
DEFAULT_PROFIT_TARGET=0.10
DEFAULT_STOP_LOSS=0.10
CONFIDENCE_THRESHOLD=0.65
VIX_HIGH_THRESHOLD=25.0
VIX_EXTREME_THRESHOLD=30.0

# Email Configuration
SMTP_TLS=true
SMTP_PORT=587
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@your-domain.com
EMAILS_FROM_NAME=Smart-0DTE-System
EOF
```

**Create Staging Environment File (.env.staging):**
```bash
# Create staging environment file (similar to production but with staging resources)
cp .env.production .env.staging

# Modify staging-specific values
sed -i 's/production/staging/g' .env.staging
sed -i 's/smart_0dte_prod/smart_0dte_staging/g' .env.staging
sed -i 's/IBKR_PAPER_TRADING=false/IBKR_PAPER_TRADING=true/g' .env.staging
sed -i 's/DEBUG=false/DEBUG=true/g' .env.staging
```

### AWS Secrets Manager Setup

Store sensitive configuration data securely using AWS Secrets Manager for production deployments.

**Create Secrets in AWS Secrets Manager:**
```bash
# Create database credentials secret
aws secretsmanager create-secret \
    --name "smart-0dte-system/database" \
    --description "Database credentials for Smart-0DTE-System" \
    --secret-string '{
        "username": "smart0dte_user",
        "password": "your-secure-database-password",
        "host": "your-rds-endpoint.region.rds.amazonaws.com",
        "port": 5432,
        "dbname": "smart_0dte_prod"
    }'

# Create API keys secret
aws secretsmanager create-secret \
    --name "smart-0dte-system/api-keys" \
    --description "API keys for Smart-0DTE-System" \
    --secret-string '{
        "databento_api_key": "your-databento-api-key",
        "ibkr_client_id": "your-ibkr-client-id",
        "jwt_secret": "your-jwt-secret-key",
        "secret_key": "your-application-secret-key"
    }'

# Create trading configuration secret
aws secretsmanager create-secret \
    --name "smart-0dte-system/trading-config" \
    --description "Trading configuration for Smart-0DTE-System" \
    --secret-string '{
        "max_positions_per_symbol": 3,
        "max_total_positions": 10,
        "default_profit_target": 0.10,
        "default_stop_loss": 0.10,
        "confidence_threshold": 0.65
    }'
```

## Infrastructure Deployment

### CloudFormation Stack Deployment

Deploy the complete AWS infrastructure using the provided CloudFormation template with comprehensive resource provisioning.

**Validate CloudFormation Template:**
```bash
# Navigate to infrastructure directory
cd infrastructure/aws/cloudformation

# Validate template syntax
aws cloudformation validate-template \
    --template-body file://smart-0dte-infrastructure.yaml

# Check template for security issues
aws cloudformation estimate-template-cost \
    --template-body file://smart-0dte-infrastructure.yaml \
    --parameters ParameterKey=Environment,ParameterValue=production
```

**Deploy Infrastructure Stack:**
```bash
# Deploy using the automated script
chmod +x ../scripts/deploy.sh

# Production deployment
../scripts/deploy.sh \
    --environment production \
    --domain-name your-domain.com \
    --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012 \
    --notification-email admin@your-domain.com \
    --key-pair-name your-ec2-key-pair

# Monitor deployment progress
aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].StackStatus'

# Watch events during deployment
aws cloudformation describe-stack-events \
    --stack-name smart-0dte-system-production \
    --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
    --output table
```

**Alternative Manual Deployment:**
```bash
# Deploy manually with specific parameters
aws cloudformation create-stack \
    --stack-name smart-0dte-system-production \
    --template-body file://smart-0dte-infrastructure.yaml \
    --parameters \
        ParameterKey=Environment,ParameterValue=production \
        ParameterKey=DomainName,ParameterValue=your-domain.com \
        ParameterKey=CertificateArn,ParameterValue=arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012 \
        ParameterKey=NotificationEmail,ParameterValue=admin@your-domain.com \
        ParameterKey=KeyPairName,ParameterValue=your-ec2-key-pair \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --enable-termination-protection

# Wait for stack creation to complete
aws cloudformation wait stack-create-complete \
    --stack-name smart-0dte-system-production
```

### Retrieve Infrastructure Outputs

After successful infrastructure deployment, retrieve important endpoint information and resource identifiers.

**Get Stack Outputs:**
```bash
# Get all stack outputs
aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs' \
    --output table

# Get specific outputs for application configuration
export VPC_ID=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`VPCId`].OutputValue' \
    --output text)

export SUBNET_IDS=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnetIds`].OutputValue' \
    --output text)

export RDS_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
    --output text)

export REDIS_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`RedisEndpoint`].OutputValue' \
    --output text)

export ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text)

export CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomain`].OutputValue' \
    --output text)

# Save outputs to file for reference
aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs' > infrastructure-outputs.json
```

## Application Deployment

### Container Image Preparation

Build and push Docker images to Amazon ECR for deployment to ECS Fargate services.

**Create ECR Repositories:**
```bash
# Create repository for backend service
aws ecr create-repository \
    --repository-name smart-0dte-system/backend \
    --region us-east-1

# Create repository for frontend service
aws ecr create-repository \
    --repository-name smart-0dte-system/frontend \
    --region us-east-1

# Get ECR login token
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

**Build and Push Backend Image:**
```bash
# Navigate to backend directory
cd backend

# Build Docker image
docker build -t smart-0dte-system/backend .

# Tag image for ECR
docker tag smart-0dte-system/backend:latest \
    $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:latest

# Push image to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:latest

# Tag and push version-specific image
docker tag smart-0dte-system/backend:latest \
    $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:v1.0.0

docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:v1.0.0
```

**Build and Push Frontend Image:**
```bash
# Navigate to frontend directory
cd ../smart-0dte-frontend

# Build production frontend
npm install
npm run build

# Create Dockerfile for frontend (if not exists)
cat > Dockerfile << 'EOF'
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

# Create nginx configuration
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;
        
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        location /api {
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
EOF

# Build and push frontend image
docker build -t smart-0dte-system/frontend .
docker tag smart-0dte-system/frontend:latest \
    $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/frontend:latest
```

### ECS Service Deployment

Deploy the application services to ECS Fargate using task definitions and service configurations.

**Create Task Definition for Backend:**
```bash
# Create backend task definition
cat > backend-task-definition.json << EOF
{
    "family": "smart-0dte-system-backend",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "1024",
    "memory": "2048",
    "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/smart-0dte-system-task-role",
    "containerDefinitions": [
        {
            "name": "backend",
            "image": "$AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "environment": [
                {
                    "name": "ENVIRONMENT",
                    "value": "production"
                },
                {
                    "name": "DATABASE_HOST",
                    "value": "$RDS_ENDPOINT"
                },
                {
                    "name": "REDIS_HOST",
                    "value": "$REDIS_ENDPOINT"
                }
            ],
            "secrets": [
                {
                    "name": "DATABASE_PASSWORD",
                    "valueFrom": "arn:aws:secretsmanager:us-east-1:$AWS_ACCOUNT_ID:secret:smart-0dte-system/database:password::"
                },
                {
                    "name": "DATABENTO_API_KEY",
                    "valueFrom": "arn:aws:secretsmanager:us-east-1:$AWS_ACCOUNT_ID:secret:smart-0dte-system/api-keys:databento_api_key::"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/smart-0dte-system-backend",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}
EOF

# Register task definition
aws ecs register-task-definition \
    --cli-input-json file://backend-task-definition.json
```

**Create and Deploy Backend Service:**
```bash
# Create backend service
aws ecs create-service \
    --cluster smart-0dte-system-cluster \
    --service-name smart-0dte-system-backend \
    --task-definition smart-0dte-system-backend:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[sg-backend],assignPublicIp=DISABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:$AWS_ACCOUNT_ID:targetgroup/smart-0dte-backend-tg,containerName=backend,containerPort=8000" \
    --enable-execute-command

# Wait for service to stabilize
aws ecs wait services-stable \
    --cluster smart-0dte-system-cluster \
    --services smart-0dte-system-backend
```

**Deploy Frontend Service:**
```bash
# Create frontend task definition and service (similar process)
# Frontend typically serves static files through CloudFront
# Upload built frontend to S3 bucket

cd ../smart-0dte-frontend
aws s3 sync dist/ s3://smart-0dte-system-frontend-bucket/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
    --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
    --paths "/*"
```

## Database Setup and Migration

### RDS PostgreSQL Configuration

Configure the RDS PostgreSQL instance with appropriate databases, users, and initial schema setup.

**Connect to RDS Instance:**
```bash
# Install PostgreSQL client
sudo apt-get install postgresql-client  # Ubuntu/Debian
brew install postgresql                  # macOS

# Connect to RDS instance
psql -h $RDS_ENDPOINT -U postgres -d postgres

# Create application database and user
CREATE DATABASE smart_0dte_prod;
CREATE USER smart0dte_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE smart_0dte_prod TO smart0dte_user;

# Connect to application database
\c smart_0dte_prod

# Grant schema permissions
GRANT ALL ON SCHEMA public TO smart0dte_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smart0dte_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smart0dte_user;

\q
```

**Run Database Migrations:**
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Set database connection environment variables
export DATABASE_URL="postgresql://smart0dte_user:your-secure-password@$RDS_ENDPOINT:5432/smart_0dte_prod"

# Run database migrations using Alembic
alembic upgrade head

# Verify tables were created
psql -h $RDS_ENDPOINT -U smart0dte_user -d smart_0dte_prod -c "\dt"
```

### Redis ElastiCache Configuration

Configure Redis ElastiCache for caching and real-time data storage with appropriate security settings.

**Test Redis Connection:**
```bash
# Install Redis CLI
sudo apt-get install redis-tools  # Ubuntu/Debian
brew install redis                # macOS

# Test connection to ElastiCache
redis-cli -h $REDIS_ENDPOINT -p 6379 ping

# Set test key-value pair
redis-cli -h $REDIS_ENDPOINT -p 6379 set test-key "Hello Smart-0DTE-System"
redis-cli -h $REDIS_ENDPOINT -p 6379 get test-key

# Check Redis info
redis-cli -h $REDIS_ENDPOINT -p 6379 info
```

**Configure Redis for Application:**
```bash
# Set application-specific Redis configuration
redis-cli -h $REDIS_ENDPOINT -p 6379 << 'EOF'
CONFIG SET maxmemory-policy allkeys-lru
CONFIG SET timeout 300
CONFIG SET tcp-keepalive 60
SAVE
EOF
```

### InfluxDB Setup (Optional)

If using InfluxDB for time-series data, configure the InfluxDB instance for market data storage.

**InfluxDB Configuration:**
```bash
# Install InfluxDB CLI
wget https://dl.influxdata.com/influxdb/releases/influxdb2-client-2.7.3-linux-amd64.tar.gz
tar xvzf influxdb2-client-2.7.3-linux-amd64.tar.gz
sudo cp influx /usr/local/bin/

# Configure InfluxDB connection
influx config create \
    --config-name smart-0dte-system \
    --host-url http://your-influxdb-endpoint:8086 \
    --org smart-0dte-system \
    --token your-influxdb-token

# Create bucket for market data
influx bucket create \
    --name market-data \
    --org smart-0dte-system \
    --retention 30d

# Verify setup
influx bucket list --org smart-0dte-system
```

## Monitoring and Logging Setup

### CloudWatch Configuration

Configure comprehensive monitoring and alerting using Amazon CloudWatch for system observability.

**Create Custom Metrics and Alarms:**
```bash
# Create alarm for high CPU usage
aws cloudwatch put-metric-alarm \
    --alarm-name "Smart-0DTE-System-High-CPU" \
    --alarm-description "Alert when CPU usage is high" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:$AWS_ACCOUNT_ID:smart-0dte-system-alerts \
    --dimensions Name=ServiceName,Value=smart-0dte-system-backend

# Create alarm for database connections
aws cloudwatch put-metric-alarm \
    --alarm-name "Smart-0DTE-System-DB-Connections" \
    --alarm-description "Alert when database connections are high" \
    --metric-name DatabaseConnections \
    --namespace AWS/RDS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:$AWS_ACCOUNT_ID:smart-0dte-system-alerts

# Create custom dashboard
aws cloudwatch put-dashboard \
    --dashboard-name "Smart-0DTE-System-Dashboard" \
    --dashboard-body file://cloudwatch-dashboard.json
```

**Create CloudWatch Dashboard Configuration (cloudwatch-dashboard.json):**
```json
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/ECS", "CPUUtilization", "ServiceName", "smart-0dte-system-backend"],
                    [".", "MemoryUtilization", ".", "."]
                ],
                "period": 300,
                "stat": "Average",
                "region": "us-east-1",
                "title": "ECS Service Metrics"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "smart-0dte-system-db"],
                    [".", "DatabaseConnections", ".", "."],
                    [".", "FreeableMemory", ".", "."]
                ],
                "period": 300,
                "stat": "Average",
                "region": "us-east-1",
                "title": "RDS Metrics"
            }
        },
        {
            "type": "log",
            "properties": {
                "query": "SOURCE '/ecs/smart-0dte-system-backend'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100",
                "region": "us-east-1",
                "title": "Recent Errors"
            }
        }
    ]
}
```

### Application Performance Monitoring

Set up application-level monitoring for trading performance and system health.

**Configure Application Metrics:**
```bash
# Create custom metrics for trading performance
aws logs create-log-group --log-group-name /smart-0dte-system/trading-metrics
aws logs create-log-group --log-group-name /smart-0dte-system/signal-performance
aws logs create-log-group --log-group-name /smart-0dte-system/risk-management

# Create metric filters for trading metrics
aws logs put-metric-filter \
    --log-group-name /smart-0dte-system/trading-metrics \
    --filter-name TradingSignals \
    --filter-pattern "[timestamp, level=INFO, message=\"Signal generated\", signal_type, confidence]" \
    --metric-transformations \
        metricName=TradingSignalsGenerated,metricNamespace=Smart0DTE/Trading,metricValue=1

aws logs put-metric-filter \
    --log-group-name /smart-0dte-system/trading-metrics \
    --filter-name SuccessfulTrades \
    --filter-pattern "[timestamp, level=INFO, message=\"Trade completed\", result=SUCCESS, pnl]" \
    --metric-transformations \
        metricName=SuccessfulTrades,metricNamespace=Smart0DTE/Trading,metricValue=1
```

## Security Configuration

### IAM Roles and Policies

Configure appropriate IAM roles and policies for secure service-to-service communication and resource access.

**Create Application-Specific IAM Policies:**
```bash
# Create policy for ECS task role
cat > smart-0dte-system-task-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:us-east-1:*:secret:smart-0dte-system/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::smart-0dte-system-storage/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:*:log-group:/smart-0dte-system/*"
            ]
        }
    ]
}
EOF

# Create IAM policy
aws iam create-policy \
    --policy-name Smart0DTESystemTaskPolicy \
    --policy-document file://smart-0dte-system-task-policy.json

# Attach policy to task role
aws iam attach-role-policy \
    --role-name smart-0dte-system-task-role \
    --policy-arn arn:aws:iam::$AWS_ACCOUNT_ID:policy/Smart0DTESystemTaskPolicy
```

### Security Group Configuration

Configure security groups for proper network access control and service isolation.

**Update Security Group Rules:**
```bash
# Get security group IDs from CloudFormation outputs
export BACKEND_SG=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`BackendSecurityGroup`].OutputValue' \
    --output text)

export DATABASE_SG=$(aws cloudformation describe-stacks \
    --stack-name smart-0dte-system-production \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseSecurityGroup`].OutputValue' \
    --output text)

# Add additional security rules if needed
aws ec2 authorize-security-group-ingress \
    --group-id $BACKEND_SG \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG

# Verify security group rules
aws ec2 describe-security-groups \
    --group-ids $BACKEND_SG $DATABASE_SG \
    --query 'SecurityGroups[*].[GroupId,IpPermissions]' \
    --output table
```

### SSL/TLS Configuration

Ensure all communications are encrypted using SSL/TLS certificates and secure protocols.

**Verify SSL Configuration:**
```bash
# Test SSL certificate on load balancer
openssl s_client -connect $ALB_DNS:443 -servername your-domain.com

# Test CloudFront SSL
openssl s_client -connect $CLOUDFRONT_DOMAIN:443 -servername your-domain.com

# Verify certificate expiration
aws acm describe-certificate \
    --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012 \
    --query 'Certificate.NotAfter'
```

## Testing and Validation

### Infrastructure Testing

Validate that all infrastructure components are properly deployed and configured.

**Test Database Connectivity:**
```bash
# Test RDS connection from ECS task
aws ecs execute-command \
    --cluster smart-0dte-system-cluster \
    --task $(aws ecs list-tasks --cluster smart-0dte-system-cluster --service-name smart-0dte-system-backend --query 'taskArns[0]' --output text) \
    --container backend \
    --interactive \
    --command "/bin/bash"

# Inside the container, test database connection
psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -c "SELECT version();"
```

**Test Redis Connectivity:**
```bash
# Test Redis connection from application
redis-cli -h $REDIS_HOST -p 6379 ping

# Test Redis performance
redis-cli -h $REDIS_HOST -p 6379 --latency-history -i 1
```

### Application Testing

Perform comprehensive testing of the deployed application to ensure all features work correctly.

**API Endpoint Testing:**
```bash
# Test health endpoint
curl -f https://your-domain.com/health

# Test API endpoints
curl -X GET https://your-domain.com/api/v1/market-data/SPY \
    -H "Authorization: Bearer your-jwt-token"

# Test WebSocket connections
wscat -c wss://your-domain.com/ws/market-data

# Load testing with Apache Bench
ab -n 1000 -c 10 https://your-domain.com/api/v1/health
```

**Frontend Testing:**
```bash
# Test frontend accessibility
curl -f https://your-domain.com/

# Test static asset loading
curl -f https://your-domain.com/assets/index.js

# Test API integration from frontend
curl -X POST https://your-domain.com/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}'
```

### Performance Testing

Conduct performance testing to ensure the system meets performance requirements under load.

**Database Performance Testing:**
```bash
# Install pgbench for PostgreSQL performance testing
sudo apt-get install postgresql-contrib

# Initialize pgbench
pgbench -h $RDS_ENDPOINT -U smart0dte_user -d smart_0dte_prod -i -s 10

# Run performance test
pgbench -h $RDS_ENDPOINT -U smart0dte_user -d smart_0dte_prod -c 10 -j 2 -t 1000
```

**Redis Performance Testing:**
```bash
# Redis benchmark
redis-benchmark -h $REDIS_ENDPOINT -p 6379 -n 10000 -c 50

# Test specific operations
redis-benchmark -h $REDIS_ENDPOINT -p 6379 -t set,get -n 100000 -q
```

## Production Checklist

### Pre-Launch Verification

Complete this checklist before launching the Smart-0DTE-System in production environment.

**Infrastructure Checklist:**
- [ ] CloudFormation stack deployed successfully
- [ ] All AWS services are running and healthy
- [ ] Security groups configured with minimal required access
- [ ] SSL certificates installed and valid
- [ ] Domain DNS records pointing to correct endpoints
- [ ] Backup and disaster recovery procedures tested

**Application Checklist:**
- [ ] Database migrations completed successfully
- [ ] All environment variables configured correctly
- [ ] API endpoints responding correctly
- [ ] Frontend application loading and functional
- [ ] WebSocket connections working
- [ ] Authentication and authorization working

**Security Checklist:**
- [ ] All secrets stored in AWS Secrets Manager
- [ ] IAM roles follow least-privilege principle
- [ ] Security groups restrict access appropriately
- [ ] SSL/TLS encryption enabled for all communications
- [ ] Database encryption at rest enabled
- [ ] Application logs do not contain sensitive information

**Monitoring Checklist:**
- [ ] CloudWatch alarms configured and tested
- [ ] Log aggregation working correctly
- [ ] Performance metrics being collected
- [ ] Alert notifications configured
- [ ] Dashboard displaying relevant metrics

**Trading System Checklist:**
- [ ] IBKR integration tested in paper trading mode
- [ ] Market data feeds connected and streaming
- [ ] Signal generation algorithms functioning
- [ ] Risk management controls active
- [ ] Position limits enforced
- [ ] Emergency halt mechanisms tested

### Launch Procedures

Follow these procedures for a smooth production launch.

**Gradual Rollout:**
```bash
# Start with minimal traffic
aws ecs update-service \
    --cluster smart-0dte-system-cluster \
    --service smart-0dte-system-backend \
    --desired-count 1

# Monitor for 30 minutes, then scale up
aws ecs update-service \
    --cluster smart-0dte-system-cluster \
    --service smart-0dte-system-backend \
    --desired-count 2

# Enable auto-scaling after successful validation
aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --scalable-dimension ecs:service:DesiredCount \
    --resource-id service/smart-0dte-system-cluster/smart-0dte-system-backend \
    --min-capacity 2 \
    --max-capacity 10
```

**Post-Launch Monitoring:**
```bash
# Monitor key metrics for first 24 hours
watch -n 30 'aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ServiceName,Value=smart-0dte-system-backend \
    --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average'

# Check application logs
aws logs tail /ecs/smart-0dte-system-backend --follow
```

## Troubleshooting

### Common Deployment Issues

Address common issues that may occur during deployment and their solutions.

**CloudFormation Stack Failures:**
```bash
# Check stack events for failure details
aws cloudformation describe-stack-events \
    --stack-name smart-0dte-system-production \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'

# Common issues and solutions:
# 1. Insufficient IAM permissions
# 2. Service limits exceeded
# 3. Invalid parameter values
# 4. Resource naming conflicts

# Rollback failed stack
aws cloudformation cancel-update-stack \
    --stack-name smart-0dte-system-production

# Delete and recreate if necessary
aws cloudformation delete-stack \
    --stack-name smart-0dte-system-production
```

**ECS Service Issues:**
```bash
# Check service status
aws ecs describe-services \
    --cluster smart-0dte-system-cluster \
    --services smart-0dte-system-backend

# Check task status
aws ecs describe-tasks \
    --cluster smart-0dte-system-cluster \
    --tasks $(aws ecs list-tasks --cluster smart-0dte-system-cluster --service-name smart-0dte-system-backend --query 'taskArns[0]' --output text)

# Check container logs
aws logs get-log-events \
    --log-group-name /ecs/smart-0dte-system-backend \
    --log-stream-name $(aws logs describe-log-streams --log-group-name /ecs/smart-0dte-system-backend --query 'logStreams[0].logStreamName' --output text)

# Common ECS issues:
# 1. Task definition errors
# 2. Network configuration issues
# 3. Health check failures
# 4. Resource constraints
```

**Database Connection Issues:**
```bash
# Test database connectivity
telnet $RDS_ENDPOINT 5432

# Check security group rules
aws ec2 describe-security-groups \
    --group-ids $DATABASE_SG \
    --query 'SecurityGroups[0].IpPermissions'

# Check RDS instance status
aws rds describe-db-instances \
    --db-instance-identifier smart-0dte-system-db

# Common database issues:
# 1. Security group not allowing connections
# 2. Database not in available state
# 3. Incorrect credentials
# 4. Network ACL restrictions
```

### Performance Issues

Diagnose and resolve performance-related problems.

**High CPU Usage:**
```bash
# Check ECS service metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ServiceName,Value=smart-0dte-system-backend \
    --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average,Maximum

# Scale up service if needed
aws ecs update-service \
    --cluster smart-0dte-system-cluster \
    --service smart-0dte-system-backend \
    --desired-count 4

# Check application logs for performance issues
aws logs filter-log-events \
    --log-group-name /ecs/smart-0dte-system-backend \
    --filter-pattern "ERROR"
```

**Database Performance Issues:**
```bash
# Check RDS performance metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name CPUUtilization \
    --dimensions Name=DBInstanceIdentifier,Value=smart-0dte-system-db \
    --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average,Maximum

# Check database connections
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name DatabaseConnections \
    --dimensions Name=DBInstanceIdentifier,Value=smart-0dte-system-db \
    --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average,Maximum

# Scale up RDS instance if needed
aws rds modify-db-instance \
    --db-instance-identifier smart-0dte-system-db \
    --db-instance-class db.t3.large \
    --apply-immediately
```

## Maintenance and Updates

### Regular Maintenance Tasks

Perform these maintenance tasks regularly to ensure optimal system performance and security.

**Weekly Maintenance:**
```bash
# Update container images
docker pull $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:latest
docker pull $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/frontend:latest

# Check for security updates
aws ecr describe-image-scan-findings \
    --repository-name smart-0dte-system/backend

# Review CloudWatch logs for errors
aws logs filter-log-events \
    --log-group-name /ecs/smart-0dte-system-backend \
    --start-time $(date -d "7 days ago" +%s)000 \
    --filter-pattern "ERROR"

# Check SSL certificate expiration
aws acm describe-certificate \
    --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012 \
    --query 'Certificate.NotAfter'
```

**Monthly Maintenance:**
```bash
# Review and optimize costs
aws ce get-cost-and-usage \
    --time-period Start=$(date -d "1 month ago" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE

# Update database statistics
psql -h $RDS_ENDPOINT -U smart0dte_user -d smart_0dte_prod -c "ANALYZE;"

# Clean up old log files
aws logs delete-log-stream \
    --log-group-name /ecs/smart-0dte-system-backend \
    --log-stream-name old-log-stream-name

# Review security group rules
aws ec2 describe-security-groups \
    --group-ids $BACKEND_SG $DATABASE_SG \
    --query 'SecurityGroups[*].[GroupId,IpPermissions]'
```

### Application Updates

Deploy application updates safely using blue-green deployment strategies.

**Blue-Green Deployment Process:**
```bash
# Build new version
docker build -t smart-0dte-system/backend:v1.1.0 backend/
docker tag smart-0dte-system/backend:v1.1.0 \
    $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:v1.1.0
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:v1.1.0

# Create new task definition with updated image
aws ecs register-task-definition \
    --family smart-0dte-system-backend \
    --container-definitions '[{
        "name": "backend",
        "image": "'$AWS_ACCOUNT_ID'.dkr.ecr.us-east-1.amazonaws.com/smart-0dte-system/backend:v1.1.0",
        ...
    }]'

# Update service with new task definition
aws ecs update-service \
    --cluster smart-0dte-system-cluster \
    --service smart-0dte-system-backend \
    --task-definition smart-0dte-system-backend:2

# Monitor deployment
aws ecs wait services-stable \
    --cluster smart-0dte-system-cluster \
    --services smart-0dte-system-backend

# Rollback if issues occur
aws ecs update-service \
    --cluster smart-0dte-system-cluster \
    --service smart-0dte-system-backend \
    --task-definition smart-0dte-system-backend:1
```

### Backup and Disaster Recovery

Implement and test backup and disaster recovery procedures.

**Database Backup:**
```bash
# Create manual snapshot
aws rds create-db-snapshot \
    --db-instance-identifier smart-0dte-system-db \
    --db-snapshot-identifier smart-0dte-system-db-$(date +%Y%m%d-%H%M%S)

# List available snapshots
aws rds describe-db-snapshots \
    --db-instance-identifier smart-0dte-system-db

# Restore from snapshot (if needed)
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier smart-0dte-system-db-restored \
    --db-snapshot-identifier smart-0dte-system-db-20231207-120000
```

**Configuration Backup:**
```bash
# Export CloudFormation template
aws cloudformation get-template \
    --stack-name smart-0dte-system-production \
    --template-stage Processed > backup-template.yaml

# Backup secrets
aws secretsmanager get-secret-value \
    --secret-id smart-0dte-system/database \
    --query SecretString > backup-database-secret.json

# Backup ECS task definitions
aws ecs describe-task-definition \
    --task-definition smart-0dte-system-backend \
    --query taskDefinition > backup-task-definition.json
```

This comprehensive cloud deployment guide provides step-by-step instructions for deploying the Smart-0DTE-System to AWS with enterprise-grade reliability, security, and scalability. Follow each section carefully and adapt the configurations to your specific requirements and environment.

