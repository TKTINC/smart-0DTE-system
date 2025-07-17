#!/bin/bash

# Smart-0DTE-System One-Click Cloud Deployment Script
# This script automates AWS infrastructure provisioning and deployment

set -e  # Exit on any error

echo "☁️  Starting Smart-0DTE-System Cloud Deployment..."
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

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install AWS CLI first."
    echo "Installation guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install Terraform first."
    echo "Installation guide: https://learn.hashicorp.com/tutorials/terraform/install-cli"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_success "Prerequisites check passed!"

# Get AWS account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

print_status "AWS Account ID: $AWS_ACCOUNT_ID"
print_status "AWS Region: $AWS_REGION"

# Navigate to terraform directory
cd terraform

# Check if terraform.tfvars exists
if [ ! -f terraform.tfvars ]; then
    print_warning "terraform.tfvars not found. Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    
    echo ""
    print_warning "Please edit terraform.tfvars with your configuration:"
    echo "  1. Set your AWS key pair name"
    echo "  2. Set a secure database password"
    echo "  3. Add your API keys (Polygon, Alpha Vantage, OpenAI)"
    echo "  4. Adjust instance types and scaling parameters as needed"
    echo ""
    read -p "Press Enter after editing terraform.tfvars to continue..."
fi

# Validate Terraform configuration
print_status "Validating Terraform configuration..."
terraform fmt
terraform validate

if [ $? -ne 0 ]; then
    print_error "Terraform configuration validation failed!"
    exit 1
fi

print_success "Terraform configuration is valid!"

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Plan deployment
print_status "Creating deployment plan..."
terraform plan -out=tfplan

echo ""
print_warning "Review the deployment plan above."
read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Deployment cancelled."
    exit 0
fi

# Apply deployment
print_status "Deploying infrastructure to AWS..."
print_status "This may take 10-15 minutes..."

terraform apply tfplan

if [ $? -ne 0 ]; then
    print_error "Terraform deployment failed!"
    exit 1
fi

# Get outputs
print_status "Retrieving deployment information..."
LOAD_BALANCER_DNS=$(terraform output -raw load_balancer_dns)
APPLICATION_URL=$(terraform output -raw load_balancer_url)

# Wait for application to be ready
print_status "Waiting for application to be ready..."
print_status "This may take 5-10 minutes for initial deployment..."

for i in {1..60}; do
    if curl -f "$APPLICATION_URL/health" &>/dev/null; then
        print_success "Application is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        print_warning "Application health check timeout. It may still be starting up."
        break
    fi
    sleep 30
done

# Display deployment summary
echo ""
echo "🎉 Smart-0DTE-System Cloud Deployment Complete!"
echo "==============================================="
echo ""
echo "📊 Application URLs:"
echo "   Frontend:     $APPLICATION_URL"
echo "   Backend API:  $APPLICATION_URL/api"
echo "   API Docs:     $APPLICATION_URL/docs"
echo "   Health Check: $APPLICATION_URL/health"
echo ""
echo "🔧 Infrastructure Details:"
echo "   Load Balancer: $LOAD_BALANCER_DNS"
echo "   AWS Region:    $AWS_REGION"
echo "   Account ID:    $AWS_ACCOUNT_ID"
echo ""
echo "📝 Next Steps:"
echo "   1. Access the application at: $APPLICATION_URL"
echo "   2. Configure IBKR connection in the application settings"
echo "   3. Monitor logs in AWS CloudWatch"
echo "   4. Set up SSL certificate for production use"
echo ""
echo "🛠️  Management Commands:"
echo "   • View infrastructure: terraform show"
echo "   • Update deployment:   terraform plan && terraform apply"
echo "   • Destroy resources:   terraform destroy"
echo ""
echo "📋 Monitoring:"
echo "   • CloudWatch Logs: /aws/ec2/smart-0dte-system"
echo "   • Auto Scaling Group: smart-0dte-asg"
echo "   • Load Balancer: smart-0dte-alb"
echo ""
print_success "Cloud deployment completed successfully!"

# Save deployment info
cat > ../deployment-info.txt << EOF
Smart-0DTE-System Cloud Deployment Information
==============================================

Deployment Date: $(date)
AWS Account ID: $AWS_ACCOUNT_ID
AWS Region: $AWS_REGION

Application URLs:
- Frontend: $APPLICATION_URL
- Backend API: $APPLICATION_URL/api
- API Documentation: $APPLICATION_URL/docs
- Health Check: $APPLICATION_URL/health

Infrastructure:
- Load Balancer DNS: $LOAD_BALANCER_DNS
- Auto Scaling Group: smart-0dte-asg
- Database: RDS PostgreSQL
- Cache: ElastiCache Redis

Management:
- Terraform state: terraform/terraform.tfstate
- AWS Console: https://console.aws.amazon.com/
- CloudWatch Logs: /aws/ec2/smart-0dte-system
EOF

print_status "Deployment information saved to deployment-info.txt"

