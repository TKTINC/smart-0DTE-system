#!/bin/bash

# Single Environment Deployment Script for Smart-0DTE + Mag7-7DTE PoC
# Usage: ./deploy-single-environment.sh [poc|single] [smart-0dte|mag7-7dte|both]

set -e  # Exit on any error

ENVIRONMENT=${1:-poc}
SYSTEM=${2:-both}

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
    echo -e "${PURPLE}[POC]${NC} $1"
}

echo "🚀 Single Environment PoC Deployment"
echo "===================================="
print_env "Environment: Single PoC Environment"
print_env "System: $SYSTEM"
print_env "Cost: ~$200/month (vs $580/month for multi-env)"
print_env "Purpose: 90-day Proof of Concept"
echo ""

# Validate system parameter
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

# Function to create single environment configuration
create_single_env_config() {
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
    
    if [ ! -d "$system_dir" ]; then
        print_error "System directory not found: $system_dir"
        return 1
    fi
    
    cd "$system_dir/terraform"
    
    # Create single environment configuration
    cat > "poc.tfvars" << EOF
# Single Environment PoC Configuration
aws_region = "us-east-1"
environment = "poc"
project_name = "${system_name}-poc"

# Single VPC configuration
vpc_cidr = "10.0.0.0/16"
admin_cidr = "0.0.0.0/0"  # Open for PoC (can restrict later)

# Single powerful instance for both dev and live trading
instance_type = "t3.xlarge"  # 4 vCPU, 16GB RAM
key_pair_name = "your-key-pair-name"  # Replace with your key pair
min_instances = 1
max_instances = 1
desired_instances = 1

# Shared database configuration
db_instance_class = "db.t3.small"
db_username = "postgres"
db_password = "poc_secure_password_123"  # Change this password

# Shared Redis configuration
redis_node_type = "cache.t3.micro"

# Live API keys (replace with your actual keys)
polygon_api_key = "your-polygon-api-key"
alpha_vantage_api_key = "your-alpha-vantage-api-key"
openai_api_key = "your-openai-api-key"

# PoC-specific settings
enable_detailed_monitoring = true
backup_retention_period = 3
multi_az = false
deletion_protection = false

# Trading configuration
paper_trading_enabled = true   # Start with paper trading
live_trading_enabled = false   # Enable when ready for live trading
debug_mode = true              # Detailed logging for PoC
max_daily_loss = 1000          # $1000 max daily loss limit
max_position_size = 5000       # $5000 max position size
EOF

    print_success "Created PoC configuration for $system_name"
    cd - > /dev/null
}

# Function to deploy single system
deploy_single_system() {
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
    
    print_status "Deploying $system_name in single PoC environment..."
    
    cd "$system_dir/terraform"
    
    # Initialize Terraform
    print_status "Initializing Terraform for $system_name..."
    terraform init
    
    # Select or create PoC workspace
    print_status "Setting up Terraform workspace: poc"
    terraform workspace select poc 2>/dev/null || terraform workspace new poc
    
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
    terraform plan -var-file="poc.tfvars" -out=tfplan-poc
    
    # Confirm deployment
    echo ""
    print_warning "Review the deployment plan for $system_name PoC environment."
    print_warning "This will create a single powerful environment for development AND live trading."
    print_warning "Estimated cost: ~$200/month"
    read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled for $system_name."
        cd - > /dev/null
        return 0
    fi
    
    # Apply deployment
    print_status "Deploying $system_name to PoC environment..."
    terraform apply tfplan-poc
    
    if [ $? -ne 0 ]; then
        print_error "Deployment failed for $system_name!"
        cd - > /dev/null
        return 1
    fi
    
    # Get outputs
    print_status "Retrieving deployment information for $system_name..."
    local app_url=$(terraform output -raw load_balancer_url 2>/dev/null || echo "Not available")
    local instance_ip=$(terraform output -raw instance_public_ip 2>/dev/null || echo "Not available")
    
    print_success "$system_name deployed successfully to PoC environment!"
    print_status "Application URL: $app_url"
    print_status "Instance IP: $instance_ip"
    
    # Create mode switching script
    cat > "../switch-mode.sh" << 'EOF'
#!/bin/bash

MODE=$1

if [ -z "$MODE" ]; then
    echo "Usage: ./switch-mode.sh <development|testing|live>"
    echo ""
    echo "Modes:"
    echo "  development - Demo APIs, paper trading, debug logging"
    echo "  testing     - Real APIs, paper trading, normal logging"
    echo "  live        - Real APIs, live trading, minimal logging"
    exit 1
fi

case $MODE in
    "development"|"dev")
        echo "🔧 Switching to DEVELOPMENT mode..."
        export TRADING_MODE="development"
        export PAPER_TRADING="true"
        export LOG_LEVEL="debug"
        export API_RATE_LIMITS="relaxed"
        echo "✅ Development mode activated"
        echo "   - Paper trading enabled"
        echo "   - Debug logging enabled"
        echo "   - Relaxed API rate limits"
        ;;
    "testing"|"test")
        echo "🧪 Switching to TESTING mode..."
        export TRADING_MODE="testing"
        export PAPER_TRADING="true"
        export LOG_LEVEL="info"
        export API_RATE_LIMITS="production"
        echo "✅ Testing mode activated"
        echo "   - Paper trading enabled"
        echo "   - Real API connections"
        echo "   - Production rate limits"
        ;;
    "live"|"production"|"prod")
        echo "🚨 Switching to LIVE TRADING mode..."
        echo "⚠️  WARNING: This will enable live trading with real money!"
        read -p "Are you sure you want to enable live trading? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Live trading mode cancelled"
            exit 0
        fi
        export TRADING_MODE="production"
        export PAPER_TRADING="false"
        export LOG_LEVEL="warning"
        export API_RATE_LIMITS="production"
        echo "🔴 LIVE TRADING mode activated"
        echo "   - LIVE TRADING ENABLED"
        echo "   - Real money at risk"
        echo "   - Minimal logging"
        ;;
    *)
        echo "❌ Invalid mode: $MODE"
        echo "Valid modes: development, testing, live"
        exit 1
        ;;
esac

# Restart services with new configuration
echo "🔄 Restarting services with new configuration..."
docker-compose down
docker-compose up -d

echo "✅ Mode switch complete!"
EOF

    chmod +x "../switch-mode.sh"
    
    # Save deployment info
    cat > "../deployment-info-poc.txt" << EOF
$system_name PoC Environment Deployment
=====================================

Deployment Date: $(date)
Environment: Single PoC Environment
System: $system_name
Terraform Workspace: poc
Estimated Cost: ~$200/month

Application URL: $app_url
Instance IP: $instance_ip
SSH Command: ssh -i ~/.ssh/your-key.pem ec2-user@$instance_ip

Mode Switching:
- Development: ./switch-mode.sh development
- Testing: ./switch-mode.sh testing
- Live Trading: ./switch-mode.sh live

Management Commands:
- View infrastructure: terraform show
- Update deployment: terraform plan -var-file="poc.tfvars" && terraform apply
- Destroy resources: terraform destroy -var-file="poc.tfvars"

PoC Success Metrics:
- Week 1-2: Basic functionality and API connections
- Week 3-4: Paper trading validation
- Week 5-8: Small live trading positions
- Week 9-12: Performance optimization and scaling
EOF
    
    cd - > /dev/null
    return 0
}

# Create configurations for selected systems
if [ "$SYSTEM" = "both" ]; then
    print_status "Creating PoC configurations for both systems..."
    create_single_env_config "smart-0dte"
    create_single_env_config "mag7-7dte"
elif [ "$SYSTEM" = "smart-0dte" ]; then
    create_single_env_config "smart-0dte"
elif [ "$SYSTEM" = "mag7-7dte" ]; then
    create_single_env_config "mag7-7dte"
fi

# Deploy based on system selection
case $SYSTEM in
    "smart-0dte")
        deploy_single_system "smart-0dte"
        ;;
    "mag7-7dte")
        deploy_single_system "mag7-7dte"
        ;;
    "both")
        print_status "Deploying both systems to single PoC environment..."
        
        # Deploy Smart-0DTE first
        deploy_single_system "smart-0dte"
        if [ $? -ne 0 ]; then
            print_error "Failed to deploy Smart-0DTE system. Aborting."
            exit 1
        fi
        
        # Wait between deployments
        print_status "Waiting 30 seconds before deploying second system..."
        sleep 30
        
        # Deploy Mag7-7DTE
        deploy_single_system "mag7-7dte"
        if [ $? -ne 0 ]; then
            print_error "Failed to deploy Mag7-7DTE system."
            exit 1
        fi
        ;;
esac

# Final summary
echo ""
echo "🎉 Single Environment PoC Deployment Complete!"
echo "=============================================="
print_env "Environment: Single PoC Environment"
print_env "System(s): $SYSTEM"
print_env "Cost: ~$200/month (66% savings vs multi-environment)"

if [ "$SYSTEM" = "both" ]; then
    echo ""
    print_success "Both trading systems deployed to single PoC environment!"
    echo ""
    echo "📊 System URLs:"
    if [ -f "smart-0DTE-system/deployment-info-poc.txt" ]; then
        SMART_URL=$(grep "Application URL:" smart-0DTE-system/deployment-info-poc.txt | cut -d' ' -f3)
        SMART_IP=$(grep "Instance IP:" smart-0DTE-system/deployment-info-poc.txt | cut -d' ' -f3)
        echo "   Smart-0DTE: $SMART_URL"
        echo "   SSH Access: ssh -i ~/.ssh/your-key.pem ec2-user@$SMART_IP"
    fi
    if [ -f "mag7-7DTE-system/deployment-info-poc.txt" ]; then
        MAG7_URL=$(grep "Application URL:" mag7-7DTE-system/deployment-info-poc.txt | cut -d' ' -f3)
        MAG7_IP=$(grep "Instance IP:" mag7-7DTE-system/deployment-info-poc.txt | cut -d' ' -f3)
        echo "   Mag7-7DTE:  $MAG7_URL"
        echo "   SSH Access: ssh -i ~/.ssh/your-key.pem ec2-user@$MAG7_IP"
    fi
fi

echo ""
echo "🔄 Environment Mode Switching:"
echo "   • Development: ./switch-mode.sh development"
echo "   • Testing:     ./switch-mode.sh testing"
echo "   • Live Trading: ./switch-mode.sh live"
echo ""
echo "🛠️  Environment Management:"
echo "   • View resources:   terraform show"
echo "   • Update deployment: terraform plan -var-file=\"poc.tfvars\" && terraform apply"
echo "   • Destroy resources: terraform destroy -var-file=\"poc.tfvars\""
echo ""
echo "📋 PoC Success Timeline:"
echo "   Week 1-2: Deploy and connect APIs"
echo "   Week 3-4: Validate paper trading"
echo "   Week 5-8: Start small live trading"
echo "   Week 9-12: Optimize and scale"
echo ""
echo "💰 Cost Optimization:"
echo "   • Single environment: ~$200/month"
echo "   • vs Multi-environment: ~$580/month"
echo "   • Savings: $380/month (66% reduction)"
echo ""
echo "🎯 Next Steps:"
echo "   1. SSH into your instance and verify applications"
echo "   2. Configure your API keys in poc.tfvars"
echo "   3. Start with development mode: ./switch-mode.sh development"
echo "   4. Test paper trading functionality"
echo "   5. When ready, switch to live trading: ./switch-mode.sh live"

print_success "Single environment PoC deployment completed successfully!"
print_warning "Remember: You can develop, test, and trade live all in this single environment!"
print_warning "This is perfect for your 90-day proof of concept period."

