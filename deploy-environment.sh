#!/bin/bash

# Multi-Environment Deployment Script for Smart-0DTE and Mag7-7DTE Systems
# Usage: ./deploy-environment.sh <dev|stage|prod> <smart-0dte|mag7-7dte|both>

set -e  # Exit on any error

ENVIRONMENT=$1
SYSTEM=$2

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

print_env() {
    echo -e "${PURPLE}[ENV]${NC} $1"
}

# Validate input parameters
if [ -z "$ENVIRONMENT" ] || [ -z "$SYSTEM" ]; then
    print_error "Usage: ./deploy-environment.sh <dev|stage|prod> <smart-0dte|mag7-7dte|both>"
    echo ""
    echo "Environments:"
    echo "  dev   - Development environment (shared resources, t3.medium)"
    echo "  stage - Staging environment (shared resources, t3.large)"
    echo "  prod  - Production environment (dedicated resources, t3.xlarge)"
    echo ""
    echo "Systems:"
    echo "  smart-0dte - Smart-0DTE-System only"
    echo "  mag7-7dte  - Mag7-7DTE-System only"
    echo "  both       - Deploy both systems"
    exit 1
fi

# Validate environment
case $ENVIRONMENT in
    "dev"|"development")
        ENVIRONMENT="dev"
        TFVARS_FILE="dev.tfvars"
        WORKSPACE="development"
        print_env "Deploying to DEVELOPMENT environment"
        ;;
    "stage"|"staging")
        ENVIRONMENT="stage"
        TFVARS_FILE="stage.tfvars"
        WORKSPACE="staging"
        print_env "Deploying to STAGING environment"
        ;;
    "prod"|"production")
        ENVIRONMENT="prod"
        TFVARS_FILE="prod.tfvars"
        WORKSPACE="production"
        print_env "Deploying to PRODUCTION environment"
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        print_error "Valid options: dev, stage, prod"
        exit 1
        ;;
esac

# Validate system
case $SYSTEM in
    "smart-0dte"|"smart-0DTE"|"smart")
        SYSTEM="smart-0dte"
        ;;
    "mag7-7dte"|"mag7-7DTE"|"mag7")
        SYSTEM="mag7-7dte"
        ;;
    "both"|"all")
        SYSTEM="both"
        ;;
    *)
        print_error "Invalid system: $SYSTEM"
        print_error "Valid options: smart-0dte, mag7-7dte, both"
        exit 1
        ;;
esac

echo "🚀 Multi-Environment Deployment Starting..."
echo "=========================================="
print_env "Environment: $ENVIRONMENT"
print_env "System: $SYSTEM"
print_env "Terraform vars: $TFVARS_FILE"
print_env "Workspace: $WORKSPACE"
echo ""

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install Terraform first."
    exit 1
fi

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install AWS CLI first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_success "Prerequisites check passed!"

# Function to deploy a single system
deploy_system() {
    local system_name=$1
    local system_dir=""
    
    case $system_name in
        "smart-0dte")
            system_dir="smart-0DTE-system"
            ;;
        "mag7-7dte")
            system_dir="mag7-7DTE-system"
            ;;
    esac
    
    print_status "Deploying $system_name to $ENVIRONMENT environment..."
    
    # Navigate to system directory
    if [ ! -d "$system_dir" ]; then
        print_error "System directory not found: $system_dir"
        return 1
    fi
    
    cd "$system_dir/terraform"
    
    # Check if environment-specific tfvars exists
    if [ ! -f "$TFVARS_FILE" ]; then
        print_warning "$TFVARS_FILE not found. Creating from template..."
        
        # Create environment-specific tfvars
        case $ENVIRONMENT in
            "dev")
                cat > "$TFVARS_FILE" << EOF
# Development Environment Configuration
aws_region = "us-east-1"
environment = "development"
project_name = "${system_name}-dev"

# Shared VPC configuration
vpc_cidr = "10.10.0.0/16"
admin_cidr = "0.0.0.0/0"

# Development instance configuration
instance_type = "t3.medium"
key_pair_name = "your-key-pair-name"
min_instances = 1
max_instances = 1
desired_instances = 1

# Shared database configuration
db_instance_class = "db.t3.micro"
db_username = "postgres"
db_password = "dev-password-123"

# Shared Redis configuration
redis_node_type = "cache.t3.micro"

# Demo API keys for development
polygon_api_key = "demo_key"
alpha_vantage_api_key = "demo_key"
openai_api_key = "demo_key"
EOF
                ;;
            "stage")
                cat > "$TFVARS_FILE" << EOF
# Staging Environment Configuration
aws_region = "us-east-1"
environment = "staging"
project_name = "${system_name}-stage"

# Shared VPC configuration
vpc_cidr = "10.10.0.0/16"
admin_cidr = "0.0.0.0/0"

# Staging instance configuration
instance_type = "t3.large"
key_pair_name = "your-key-pair-name"
min_instances = 1
max_instances = 2
desired_instances = 1

# Shared database configuration
db_instance_class = "db.t3.small"
db_username = "postgres"
db_password = "stage-password-123"

# Shared Redis configuration
redis_node_type = "cache.t3.small"

# Production-like API keys
polygon_api_key = "your-polygon-api-key"
alpha_vantage_api_key = "your-alpha-vantage-api-key"
openai_api_key = "your-openai-api-key"
EOF
                ;;
            "prod")
                cat > "$TFVARS_FILE" << EOF
# Production Environment Configuration
aws_region = "us-east-1"
environment = "production"
project_name = "${system_name}-prod"

# Dedicated VPC configuration
vpc_cidr = "10.0.0.0/16"
admin_cidr = "your-ip-address/32"  # Restrict to your IP

# Production instance configuration
instance_type = "t3.xlarge"
key_pair_name = "your-key-pair-name"
min_instances = 2
max_instances = 5
desired_instances = 2

# Dedicated database configuration
db_instance_class = "db.t3.medium"
db_username = "postgres"
db_password = "secure-production-password"

# Dedicated Redis configuration
redis_node_type = "cache.t3.small"

# Production API keys
polygon_api_key = "your-production-polygon-api-key"
alpha_vantage_api_key = "your-production-alpha-vantage-api-key"
openai_api_key = "your-production-openai-api-key"
EOF
                ;;
        esac
        
        print_warning "Please edit $TFVARS_FILE with your actual configuration before proceeding."
        read -p "Press Enter after editing the configuration file..."
    fi
    
    # Initialize Terraform
    print_status "Initializing Terraform for $system_name..."
    terraform init
    
    # Select or create workspace
    print_status "Setting up Terraform workspace: $WORKSPACE"
    terraform workspace select "$WORKSPACE" 2>/dev/null || terraform workspace new "$WORKSPACE"
    
    # Validate configuration
    print_status "Validating Terraform configuration..."
    terraform validate
    
    if [ $? -ne 0 ]; then
        print_error "Terraform validation failed for $system_name!"
        cd - > /dev/null
        return 1
    fi
    
    # Plan deployment
    print_status "Creating deployment plan for $system_name..."
    terraform plan -var-file="$TFVARS_FILE" -out=tfplan-$ENVIRONMENT
    
    # Confirm deployment
    echo ""
    print_warning "Review the deployment plan for $system_name in $ENVIRONMENT environment."
    read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled for $system_name."
        cd - > /dev/null
        return 0
    fi
    
    # Apply deployment
    print_status "Deploying $system_name to $ENVIRONMENT environment..."
    terraform apply tfplan-$ENVIRONMENT
    
    if [ $? -ne 0 ]; then
        print_error "Deployment failed for $system_name!"
        cd - > /dev/null
        return 1
    fi
    
    # Get outputs
    print_status "Retrieving deployment information for $system_name..."
    local app_url=$(terraform output -raw load_balancer_url 2>/dev/null || echo "Not available")
    
    print_success "$system_name deployed successfully to $ENVIRONMENT!"
    print_status "Application URL: $app_url"
    
    # Save deployment info
    cat > "../deployment-info-$ENVIRONMENT.txt" << EOF
$system_name $ENVIRONMENT Environment Deployment
=============================================

Deployment Date: $(date)
Environment: $ENVIRONMENT
System: $system_name
Terraform Workspace: $WORKSPACE

Application URL: $app_url
Terraform State: terraform/terraform.tfstate

Management Commands:
- View infrastructure: terraform show
- Update deployment: terraform plan -var-file="$TFVARS_FILE" && terraform apply
- Destroy resources: terraform destroy -var-file="$TFVARS_FILE"
EOF
    
    cd - > /dev/null
    return 0
}

# Deploy based on system selection
case $SYSTEM in
    "smart-0dte")
        deploy_system "smart-0dte"
        ;;
    "mag7-7dte")
        deploy_system "mag7-7dte"
        ;;
    "both")
        print_status "Deploying both systems to $ENVIRONMENT environment..."
        
        # Deploy Smart-0DTE first
        deploy_system "smart-0dte"
        if [ $? -ne 0 ]; then
            print_error "Failed to deploy Smart-0DTE system. Aborting."
            exit 1
        fi
        
        # Wait between deployments
        print_status "Waiting 30 seconds before deploying second system..."
        sleep 30
        
        # Deploy Mag7-7DTE
        deploy_system "mag7-7dte"
        if [ $? -ne 0 ]; then
            print_error "Failed to deploy Mag7-7DTE system."
            exit 1
        fi
        ;;
esac

# Final summary
echo ""
echo "🎉 Multi-Environment Deployment Complete!"
echo "========================================"
print_env "Environment: $ENVIRONMENT"
print_env "System(s): $SYSTEM"

if [ "$SYSTEM" = "both" ]; then
    echo ""
    print_success "Both trading systems deployed successfully!"
    echo ""
    echo "📊 System URLs:"
    if [ -f "smart-0DTE-system/deployment-info-$ENVIRONMENT.txt" ]; then
        SMART_URL=$(grep "Application URL:" smart-0DTE-system/deployment-info-$ENVIRONMENT.txt | cut -d' ' -f3)
        echo "   Smart-0DTE: $SMART_URL"
    fi
    if [ -f "mag7-7DTE-system/deployment-info-$ENVIRONMENT.txt" ]; then
        MAG7_URL=$(grep "Application URL:" mag7-7DTE-system/deployment-info-$ENVIRONMENT.txt | cut -d' ' -f3)
        echo "   Mag7-7DTE:  $MAG7_URL"
    fi
fi

echo ""
echo "🛠️  Environment Management:"
echo "   • Switch workspace: terraform workspace select $WORKSPACE"
echo "   • View resources:   terraform show"
echo "   • Update deployment: terraform plan -var-file=\"$TFVARS_FILE\" && terraform apply"
echo "   • Destroy resources: terraform destroy -var-file=\"$TFVARS_FILE\""
echo ""
echo "📋 Next Steps:"
echo "   1. Verify applications are accessible"
echo "   2. Configure API keys in $TFVARS_FILE"
echo "   3. Test trading functionality"
echo "   4. Set up monitoring and alerts"
echo ""

case $ENVIRONMENT in
    "dev")
        echo "💡 Development Environment Notes:"
        echo "   • Uses shared resources for cost optimization"
        echo "   • Demo API keys are configured"
        echo "   • SSH access is open for debugging"
        echo "   • Minimal backups and monitoring"
        ;;
    "stage")
        echo "🧪 Staging Environment Notes:"
        echo "   • Uses shared resources with production-like sizing"
        echo "   • Production API keys should be configured"
        echo "   • Enhanced monitoring enabled"
        echo "   • Used for final testing before production"
        ;;
    "prod")
        echo "🏭 Production Environment Notes:"
        echo "   • Dedicated resources for performance and isolation"
        echo "   • Production API keys required"
        echo "   • Full monitoring and backup enabled"
        echo "   • Multi-AZ deployment for high availability"
        ;;
esac

print_success "Multi-environment deployment completed successfully!"

