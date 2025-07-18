# Smart-0DTE-System: Multi-Environment Deployment Guide

**Author**: Manus AI  
**Date**: July 17, 2025  
**Version**: 1.0  
**Document Type**: Step-by-Step Deployment Guide

## 🎯 Overview

This guide provides detailed, step-by-step instructions for deploying the Smart-0DTE-System across Development, Staging, and Production environments in AWS. Follow this guide after completing the AWS account setup from the [AWS Cloud Provisioning Guide](./AWS-CLOUD-PROVISIONING-GUIDE-UPDATED.md).

## 📋 Prerequisites Checklist

Before starting deployment, ensure you have completed:

### ✅ **AWS Account Setup**
- [ ] AWS account created and verified
- [ ] Root account MFA enabled
- [ ] Billing alerts configured
- [ ] IAM user created with appropriate permissions
- [ ] AWS CLI installed and configured

### ✅ **Local Development Environment**
- [ ] Git installed and configured
- [ ] Terraform installed (version 1.0+)
- [ ] AWS CLI installed and configured
- [ ] SSH key pair created for EC2 access
- [ ] Code editor/IDE set up

### ✅ **Repository Access**
- [ ] Smart-0DTE-System repository cloned
- [ ] Environment variables template reviewed
- [ ] API keys obtained (Polygon, Alpha Vantage, OpenAI)

## 🚀 Phase 1: Development Environment Deployment

### Step 1: Repository Setup and Configuration

```bash
# Clone the repository if not already done
git clone https://github.com/TKTINC/smart-0DTE-system.git
cd smart-0DTE-system

# Verify deployment script is executable
chmod +x deploy-environment.sh

# Check current directory structure
ls -la
```

### Step 2: Configure Development Environment Variables

Create and configure the development environment variables:

```bash
# Navigate to terraform directory
cd terraform

# Create development configuration file
cp terraform.tfvars.example dev.tfvars

# Edit development configuration
nano dev.tfvars
```

**Development Configuration (dev.tfvars):**
```hcl
# Development Environment Configuration
aws_region = "us-east-1"
environment = "development"
project_name = "smart-0dte-dev"

# VPC Configuration
vpc_cidr = "10.10.0.0/16"
admin_cidr = "0.0.0.0/0"  # Open for development (restrict in production)

# Instance Configuration
instance_type = "t3.medium"
key_pair_name = "your-aws-key-pair-name"  # Replace with your key pair
min_instances = 1
max_instances = 1
desired_instances = 1

# Database Configuration (Shared)
db_instance_class = "db.t3.small"
db_username = "postgres"
db_password = "dev_secure_password_123"  # Change this password

# Redis Configuration (Shared)
redis_node_type = "cache.t3.micro"

# API Keys (Use demo keys for development)
polygon_api_key = "demo_key"
alpha_vantage_api_key = "demo_key"
openai_api_key = "demo_key"

# Development-specific settings
enable_detailed_monitoring = false
backup_retention_period = 1
multi_az = false
deletion_protection = false
```

### Step 3: Deploy Development Environment

```bash
# Return to root directory
cd ..

# Deploy development environment
./deploy-environment.sh dev smart-0dte

# Monitor deployment progress
# This will take approximately 10-15 minutes
```

**Expected Output:**
```
🚀 Multi-Environment Deployment Starting...
==========================================
Environment: dev
System: smart-0dte
Terraform vars: dev.tfvars
Workspace: development

✅ Prerequisites check passed!
📋 Initializing Terraform...
🔧 Selecting workspace: development
📊 Planning deployment...
🚀 Deploying smart-0dte to development environment...
✅ smart-0dte deployed successfully to development!
```

### Step 4: Verify Development Deployment

```bash
# Check deployment status
cd smart-0DTE-system/terraform
terraform workspace select development
terraform show

# Get application URL
terraform output load_balancer_url

# Test application health
curl http://$(terraform output -raw load_balancer_url)/health
```

### Step 5: Access Development Environment

```bash
# SSH into development instance
ssh -i ~/.ssh/your-key.pem ec2-user@$(terraform output -raw instance_public_ip)

# Check application status
sudo docker-compose ps
sudo systemctl status smart-0dte-system

# View application logs
sudo docker-compose logs -f backend
```

## 🧪 Phase 2: Staging Environment Deployment

### Step 1: Configure Staging Environment

```bash
# Create staging configuration
cd terraform
cp dev.tfvars stage.tfvars

# Edit staging configuration
nano stage.tfvars
```

**Staging Configuration (stage.tfvars):**
```hcl
# Staging Environment Configuration
aws_region = "us-east-1"
environment = "staging"
project_name = "smart-0dte-stage"

# VPC Configuration (Shared with dev)
vpc_cidr = "10.10.0.0/16"
admin_cidr = "your-ip-address/32"  # Restrict to your IP

# Instance Configuration (Larger for staging)
instance_type = "t3.large"
key_pair_name = "your-aws-key-pair-name"
min_instances = 1
max_instances = 2
desired_instances = 1

# Database Configuration (Shared with dev)
db_instance_class = "db.t3.small"
db_username = "postgres"
db_password = "stage_secure_password_456"  # Different password

# Redis Configuration (Shared with dev)
redis_node_type = "cache.t3.small"

# API Keys (Production-like keys for staging)
polygon_api_key = "your-polygon-api-key"
alpha_vantage_api_key = "your-alpha-vantage-api-key"
openai_api_key = "your-openai-api-key"

# Staging-specific settings
enable_detailed_monitoring = true
backup_retention_period = 3
multi_az = false
deletion_protection = false
```

### Step 2: Deploy Staging Environment

```bash
# Return to root directory
cd ..

# Deploy staging environment
./deploy-environment.sh stage smart-0dte

# Wait for deployment completion (10-15 minutes)
```

### Step 3: Verify Staging Deployment

```bash
# Check staging deployment
cd smart-0DTE-system/terraform
terraform workspace select staging
terraform show

# Test staging application
curl http://$(terraform output -raw load_balancer_url)/health

# Run integration tests
pytest tests/integration/ --env=staging
```

## 🏭 Phase 3: Production Environment Deployment

### Step 1: Configure Production Environment

```bash
# Create production configuration
cd terraform
cp stage.tfvars prod.tfvars

# Edit production configuration carefully
nano prod.tfvars
```

**Production Configuration (prod.tfvars):**
```hcl
# Production Environment Configuration
aws_region = "us-east-1"
environment = "production"
project_name = "smart-0dte-prod"

# VPC Configuration (Dedicated for production)
vpc_cidr = "10.0.0.0/16"
admin_cidr = "your-ip-address/32"  # Restrict to your IP only

# Instance Configuration (High performance)
instance_type = "t3.xlarge"
key_pair_name = "your-aws-key-pair-name"
min_instances = 2
max_instances = 5
desired_instances = 2

# Database Configuration (Dedicated)
db_instance_class = "db.t3.medium"
db_username = "postgres"
db_password = "production_ultra_secure_password_789"  # Very secure password

# Redis Configuration (Dedicated)
redis_node_type = "cache.t3.small"

# API Keys (Production keys)
polygon_api_key = "your-production-polygon-api-key"
alpha_vantage_api_key = "your-production-alpha-vantage-api-key"
openai_api_key = "your-production-openai-api-key"

# Production settings
enable_detailed_monitoring = true
backup_retention_period = 7
multi_az = true
deletion_protection = true
```

### Step 2: Deploy Production Environment

```bash
# Return to root directory
cd ..

# Deploy production environment (requires confirmation)
./deploy-environment.sh prod smart-0dte

# This will prompt for confirmation before deploying
# Review the plan carefully before confirming
```

### Step 3: Verify Production Deployment

```bash
# Check production deployment
cd smart-0DTE-system/terraform
terraform workspace select production
terraform show

# Test production application
curl http://$(terraform output -raw load_balancer_url)/health

# Run smoke tests
pytest tests/smoke/ --env=production
```

## 🔄 Phase 4: Deploy Both Systems (Smart-0DTE + Mag7-7DTE)

### Step 1: Deploy Mag7-7DTE to All Environments

```bash
# Deploy Mag7-7DTE to development
./deploy-environment.sh dev mag7-7dte

# Deploy Mag7-7DTE to staging
./deploy-environment.sh stage mag7-7dte

# Deploy Mag7-7DTE to production
./deploy-environment.sh prod mag7-7dte
```

### Step 2: Unified Deployment Option

```bash
# Deploy both systems to all environments
./deploy-environment.sh dev both
./deploy-environment.sh stage both
./deploy-environment.sh prod both
```

## 📊 Phase 5: Environment Verification and Testing

### Development Environment Testing

```bash
# Connect to development environment
ssh -i ~/.ssh/your-key.pem ec2-user@dev-smart-0dte.your-domain.com

# Run development tests
cd /opt/smart-0dte-system
python -m pytest tests/unit/ -v
python -m pytest tests/integration/basic/ -v

# Test trading functionality with paper trading
curl -X POST http://localhost:8000/api/v1/trading/test-signal \
  -H "Content-Type: application/json" \
  -d '{"symbol": "SPY", "strategy": "0dte_momentum"}'

# Check system health
curl http://localhost:8000/health
curl http://localhost:3000  # Frontend health
```

### Staging Environment Testing

```bash
# Connect to staging environment
ssh -i ~/.ssh/your-key.pem ec2-user@stage-smart-0dte.your-domain.com

# Run comprehensive test suite
cd /opt/smart-0dte-system
python -m pytest tests/ -v --env=staging

# Performance testing
k6 run tests/performance/load-test.js

# Integration testing with real market data
python scripts/test-market-data-integration.py --env=staging
```

### Production Environment Testing

```bash
# Production testing (limited to smoke tests)
curl https://prod-smart-0dte.your-domain.com/health
curl https://prod-smart-0dte.your-domain.com/api/v1/system/status

# Monitor production metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistics Average \
  --start-time 2025-07-17T00:00:00Z \
  --end-time 2025-07-17T23:59:59Z \
  --period 3600
```

## 🛠️ Phase 6: Environment Management and Operations

### Daily Operations

#### **Development Environment**
```bash
# Start development work
ssh -i ~/.ssh/your-key.pem ec2-user@dev-smart-0dte.your-domain.com

# Pull latest code
cd /opt/smart-0dte-system
git pull origin develop

# Restart services with new code
sudo docker-compose down
sudo docker-compose up -d

# Monitor logs
sudo docker-compose logs -f backend
```

#### **Staging Environment**
```bash
# Deploy to staging for testing
git checkout staging
git merge develop
git push origin staging

# Automated deployment will trigger
# Monitor deployment status
./deploy-environment.sh stage smart-0dte

# Run integration tests
pytest tests/integration/ --env=staging
```

#### **Production Environment**
```bash
# Production deployment (after staging approval)
git checkout main
git merge staging
git push origin main

# Deploy to production
./deploy-environment.sh prod smart-0dte

# Monitor production health
aws cloudwatch get-dashboard --dashboard-name Smart0DTEProduction
```

### Environment Scaling

#### **Scale Development Environment**
```bash
# Increase development instance size if needed
cd smart-0DTE-system/terraform
terraform workspace select development

# Edit dev.tfvars
nano dev.tfvars
# Change: instance_type = "t3.large"

# Apply changes
terraform plan -var-file="dev.tfvars"
terraform apply -var-file="dev.tfvars"
```

#### **Scale Production Environment**
```bash
# Scale production auto scaling group
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name smart-0dte-production-asg \
  --desired-capacity 3 \
  --max-size 6
```

### Environment Monitoring

#### **Set Up CloudWatch Dashboards**
```bash
# Create development dashboard
aws cloudwatch put-dashboard \
  --dashboard-name Smart0DTEDevelopment \
  --dashboard-body file://cloudwatch-dev-dashboard.json

# Create production dashboard
aws cloudwatch put-dashboard \
  --dashboard-name Smart0DTEProduction \
  --dashboard-body file://cloudwatch-prod-dashboard.json
```

#### **Set Up Alerts**
```bash
# CPU utilization alert for production
aws cloudwatch put-metric-alarm \
  --alarm-name "Smart0DTE-Prod-HighCPU" \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## 🔧 Troubleshooting Common Issues

### Deployment Failures

#### **Terraform State Issues**
```bash
# If terraform state is corrupted
terraform workspace select development
terraform refresh -var-file="dev.tfvars"

# If state is completely broken
terraform import aws_instance.dev_app i-1234567890abcdef0
```

#### **Resource Conflicts**
```bash
# If resources already exist
terraform import aws_vpc.shared_dev_stage vpc-12345678
terraform import aws_subnet.dev_private subnet-12345678
```

### Application Issues

#### **Database Connection Problems**
```bash
# Check database connectivity
psql -h shared-dev-postgres.region.rds.amazonaws.com -U postgres -d smart_0dte_dev

# Check security groups
aws ec2 describe-security-groups --group-ids sg-12345678
```

#### **Redis Connection Problems**
```bash
# Test Redis connectivity
redis-cli -h shared-dev-redis.region.cache.amazonaws.com ping

# Check Redis configuration
aws elasticache describe-replication-groups --replication-group-id shared-dev-stage-redis
```

### Performance Issues

#### **High CPU Usage**
```bash
# Check instance metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --statistics Average \
  --start-time 2025-07-17T00:00:00Z \
  --end-time 2025-07-17T23:59:59Z \
  --period 300

# Scale up if needed
terraform apply -var="instance_type=t3.large" -var-file="dev.tfvars"
```

## 📈 Next Steps After Deployment

### 1. **Configure Monitoring and Alerting**
- Set up CloudWatch dashboards
- Configure SNS notifications
- Implement custom metrics for trading performance

### 2. **Set Up CI/CD Pipeline**
- Configure GitHub Actions for automated deployment
- Set up automated testing pipeline
- Implement blue-green deployment for production

### 3. **Security Hardening**
- Implement AWS WAF for web application firewall
- Set up VPC Flow Logs for network monitoring
- Configure AWS Config for compliance monitoring

### 4. **Performance Optimization**
- Implement caching strategies
- Optimize database queries
- Set up auto-scaling policies

### 5. **Backup and Disaster Recovery**
- Configure automated backups
- Test disaster recovery procedures
- Implement cross-region replication for critical data

## 🏆 Deployment Success Checklist

### ✅ **Development Environment**
- [ ] Development environment deployed successfully
- [ ] Application accessible via load balancer URL
- [ ] Database connectivity verified
- [ ] Redis connectivity verified
- [ ] Unit tests passing
- [ ] Basic integration tests passing

### ✅ **Staging Environment**
- [ ] Staging environment deployed successfully
- [ ] Production-like API keys configured
- [ ] Full test suite passing
- [ ] Performance tests completed
- [ ] Load testing completed

### ✅ **Production Environment**
- [ ] Production environment deployed successfully
- [ ] High availability configuration verified
- [ ] Monitoring and alerting configured
- [ ] Backup procedures tested
- [ ] Security hardening completed
- [ ] Smoke tests passing

### ✅ **Both Systems Deployed**
- [ ] Smart-0DTE system deployed to all environments
- [ ] Mag7-7DTE system deployed to all environments
- [ ] Cross-system integration tested
- [ ] Unified monitoring dashboard configured

## 💰 Cost Monitoring

### Monthly Cost Tracking
```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2025-07-01,End=2025-07-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Set up cost alerts
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget-config.json
```

### Expected Monthly Costs
- **Development**: $35/month
- **Staging**: $65/month  
- **Production**: $435/month
- **Shared Infrastructure**: $45/month
- **Total**: $580/month

This comprehensive deployment guide ensures successful deployment of both Smart-0DTE and Mag7-7DTE systems across all environments with proper testing, monitoring, and operational procedures.

