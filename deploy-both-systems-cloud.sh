#!/bin/bash

# Unified Cloud Deployment Script for Both Trading Systems
# This script deploys both Smart-0DTE-System and Mag7-7DTE-System to AWS

set -e  # Exit on any error

echo "☁️  Starting Unified Cloud Deployment of Both Trading Systems..."
echo "==============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

print_cloud() {
    echo -e "${CYAN}[CLOUD]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites for cloud deployment..."

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

print_cloud "AWS Account ID: $AWS_ACCOUNT_ID"
print_cloud "AWS Region: $AWS_REGION"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# System paths
SMART_0DTE_DIR="$SCRIPT_DIR/smart-0DTE-system"
MAG7_7DTE_DIR="$SCRIPT_DIR/mag7-7DTE-system"

# Check if both system directories exist
if [ ! -d "$SMART_0DTE_DIR" ]; then
    print_error "Smart-0DTE-System directory not found at $SMART_0DTE_DIR"
    exit 1
fi

if [ ! -d "$MAG7_7DTE_DIR" ]; then
    print_error "Mag7-7DTE-System directory not found at $MAG7_7DTE_DIR"
    exit 1
fi

# Function to deploy a system to cloud
deploy_system_cloud() {
    local system_name=$1
    local system_dir=$2
    
    print_system "Deploying $system_name to AWS Cloud..."
    
    cd "$system_dir/terraform"
    
    # Check if terraform.tfvars exists
    if [ ! -f terraform.tfvars ]; then
        print_warning "terraform.tfvars not found for $system_name. Creating from example..."
        cp terraform.tfvars.example terraform.tfvars
        
        echo ""
        print_warning "Please edit $system_dir/terraform/terraform.tfvars with your configuration:"
        echo "  1. Set your AWS key pair name"
        echo "  2. Set secure passwords"
        echo "  3. Add your API keys"
        echo "  4. Adjust instance types as needed"
        echo ""
        read -p "Press Enter after editing terraform.tfvars to continue..."
    fi
    
    # Validate Terraform configuration
    print_status "Validating $system_name Terraform configuration..."
    terraform fmt
    terraform validate
    
    if [ $? -ne 0 ]; then
        print_error "$system_name Terraform configuration validation failed!"
        return 1
    fi
    
    # Initialize Terraform
    print_status "Initializing $system_name Terraform..."
    terraform init
    
    # Plan deployment
    print_status "Creating $system_name deployment plan..."
    terraform plan -out=tfplan
    
    echo ""
    print_warning "Review the $system_name deployment plan above."
    read -p "Do you want to proceed with $system_name deployment? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "$system_name deployment skipped."
        cd - > /dev/null
        return 0
    fi
    
    # Apply deployment
    print_status "Deploying $system_name infrastructure to AWS..."
    terraform apply tfplan
    
    if [ $? -ne 0 ]; then
        print_error "$system_name deployment failed!"
        cd - > /dev/null
        return 1
    fi
    
    # Get outputs
    local load_balancer_dns=$(terraform output -raw load_balancer_dns)
    local application_url=$(terraform output -raw load_balancer_url)
    
    print_success "$system_name infrastructure deployed successfully!"
    print_status "$system_name URL: $application_url"
    
    # Wait for application to be ready
    print_status "Waiting for $system_name application to be ready..."
    for i in {1..60}; do
        if curl -f "$application_url/health" &>/dev/null; then
            print_success "$system_name application is ready!"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "$system_name application health check timeout. It may still be starting up."
            break
        fi
        sleep 30
    done
    
    # Save deployment info for this system
    cat > "../deployment-info-cloud.txt" << EOF
$system_name Cloud Deployment Information
========================================

Deployment Date: $(date)
AWS Account ID: $AWS_ACCOUNT_ID
AWS Region: $AWS_REGION

Application URLs:
- Frontend: $application_url
- Backend API: $application_url/api
- API Documentation: $application_url/docs
- Health Check: $application_url/health

Infrastructure:
- Load Balancer DNS: $load_balancer_dns
- Terraform state: terraform/terraform.tfstate
EOF
    
    cd - > /dev/null
    return 0
}

# Ask user which systems to deploy
echo ""
echo "Which systems would you like to deploy to AWS Cloud?"
echo "1) Smart-0DTE-System only"
echo "2) Mag7-7DTE-System only"
echo "3) Both systems"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        print_system "Deploying Smart-0DTE-System to cloud..."
        deploy_system_cloud "Smart-0DTE-System" "$SMART_0DTE_DIR"
        ;;
    2)
        print_system "Deploying Mag7-7DTE-System to cloud..."
        deploy_system_cloud "Mag7-7DTE-System" "$MAG7_7DTE_DIR"
        ;;
    3)
        print_system "Deploying both systems to cloud..."
        
        # Deploy Smart-0DTE-System first
        deploy_system_cloud "Smart-0DTE-System" "$SMART_0DTE_DIR"
        
        # Wait between deployments
        sleep 30
        
        # Deploy Mag7-7DTE-System
        deploy_system_cloud "Mag7-7DTE-System" "$MAG7_7DTE_DIR"
        ;;
    *)
        print_error "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Final summary
echo ""
echo "🎉 Cloud Deployment Summary"
echo "=========================="

if [ "$choice" = "1" ] || [ "$choice" = "3" ]; then
    if [ -f "$SMART_0DTE_DIR/deployment-info-cloud.txt" ]; then
        echo ""
        print_system "Smart-0DTE-System (0-Day-To-Expiration ETF Options):"
        SMART_URL=$(cd "$SMART_0DTE_DIR/terraform" && terraform output -raw load_balancer_url 2>/dev/null || echo "Not available")
        echo "   Application URL: $SMART_URL"
        echo "   Strategy: Intraday ETF options (SPY, QQQ, IWM, VIX)"
        echo "   Infrastructure: Standard AWS deployment"
    fi
fi

if [ "$choice" = "2" ] || [ "$choice" = "3" ]; then
    if [ -f "$MAG7_7DTE_DIR/deployment-info-cloud.txt" ]; then
        echo ""
        print_system "Mag7-7DTE-System (7-Day-To-Expiration Magnificent 7 Stocks):"
        MAG7_URL=$(cd "$MAG7_7DTE_DIR/terraform" && terraform output -raw load_balancer_url 2>/dev/null || echo "Not available")
        echo "   Application URL: $MAG7_URL"
        echo "   Strategy: 7-day options on AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META"
        echo "   Infrastructure: Enhanced AWS deployment with dedicated InfluxDB"
    fi
fi

echo ""
echo "📝 Important Cloud Notes:"
echo "   • Both systems use separate VPCs to avoid conflicts"
echo "   • Each system has its own database and caching infrastructure"
echo "   • Monitor costs in AWS Billing Dashboard"
echo "   • Use CloudWatch for monitoring and logging"
echo "   • Set up SSL certificates for production use"
echo ""
echo "🛠️  Management Commands:"
echo "   • View infrastructure: cd [system]/terraform && terraform show"
echo "   • Update deployment:   cd [system]/terraform && terraform plan && terraform apply"
echo "   • Destroy resources:   cd [system]/terraform && terraform destroy"
echo ""
echo "💰 Cost Optimization:"
echo "   • Stop instances during non-trading hours if needed"
echo "   • Use Reserved Instances for production workloads"
echo "   • Monitor CloudWatch costs and set up billing alerts"
echo ""
print_success "All selected systems deployed to AWS cloud successfully!"

# Create unified deployment summary
cat > deployment-summary-cloud.txt << EOF
Unified Cloud Deployment Summary
===============================

Deployment Date: $(date)
AWS Account ID: $AWS_ACCOUNT_ID
AWS Region: $AWS_REGION

Systems Deployed:
EOF

if [ "$choice" = "1" ] || [ "$choice" = "3" ]; then
    SMART_URL=$(cd "$SMART_0DTE_DIR/terraform" && terraform output -raw load_balancer_url 2>/dev/null || echo "Not available")
    cat >> deployment-summary-cloud.txt << EOF

Smart-0DTE-System:
- URL: $SMART_URL
- Strategy: 0-day ETF options
- Infrastructure: Standard AWS deployment
EOF
fi

if [ "$choice" = "2" ] || [ "$choice" = "3" ]; then
    MAG7_URL=$(cd "$MAG7_7DTE_DIR/terraform" && terraform output -raw load_balancer_url 2>/dev/null || echo "Not available")
    cat >> deployment-summary-cloud.txt << EOF

Mag7-7DTE-System:
- URL: $MAG7_URL
- Strategy: 7-day Magnificent 7 options
- Infrastructure: Enhanced AWS deployment
EOF
fi

print_status "Unified deployment summary saved to deployment-summary-cloud.txt"

