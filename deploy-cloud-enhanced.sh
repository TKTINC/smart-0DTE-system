#!/bin/bash

# Enhanced Smart-0DTE-System Cloud Deployment Script
# Implements all security and reliability improvements from code review

# Strict error handling
set -Eeuo pipefail
IFS=$'\n\t'

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Script configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"
readonly TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"
readonly LOG_DIR="$PROJECT_ROOT/logs"
readonly TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
readonly LOG_FILE="$LOG_DIR/deployment_${TIMESTAMP}.log"

# Default values
ENVIRONMENT="${1:-dev}"
AUTO_APPROVE="${AUTO_APPROVE:-false}"
SKIP_BUILD="${SKIP_BUILD:-false}"
DOMAIN_NAME="${DOMAIN_NAME:-}"
ENABLE_HTTPS="${ENABLE_HTTPS:-true}"

# Trap errors and provide cleanup
trap 'error_handler $? $LINENO' ERR
trap 'cleanup' EXIT

error_handler() {
    local exit_code=$1
    local line_number=$2
    echo -e "\n${RED}✖ Error on line $line_number (exit code: $exit_code)${NC}" >&2
    echo -e "${RED}✖ Deployment failed. Check logs: $LOG_FILE${NC}" >&2
    
    if [[ "$exit_code" -ne 0 ]]; then
        echo -e "${YELLOW}⚠ Consider running: terraform destroy${NC}" >&2
        echo -e "${YELLOW}⚠ Or use: $0 --destroy to clean up resources${NC}" >&2
    fi
}

cleanup() {
    # Clean up temporary files if any
    if [[ -f "$TERRAFORM_DIR/tfplan" ]]; then
        rm -f "$TERRAFORM_DIR/tfplan"
    fi
}

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")  echo -e "${GREEN}ℹ $message${NC}" ;;
        "WARN")  echo -e "${YELLOW}⚠ $message${NC}" ;;
        "ERROR") echo -e "${RED}✖ $message${NC}" ;;
        "DEBUG") echo -e "${BLUE}🔍 $message${NC}" ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

show_usage() {
    cat << EOF
Usage: $0 [ENVIRONMENT] [OPTIONS]

ENVIRONMENT:
    dev     Deploy to development environment (default)
    prod    Deploy to production environment

OPTIONS:
    --auto-approve    Skip interactive approval for terraform apply
    --skip-build      Skip Docker image build and push
    --domain=DOMAIN   Set custom domain name for HTTPS
    --no-https        Disable HTTPS/TLS configuration
    --destroy         Destroy infrastructure instead of deploying
    --help           Show this help message

EXAMPLES:
    $0 dev                          # Deploy to dev with interactive approval
    $0 prod --auto-approve          # Deploy to prod with auto-approval
    $0 dev --domain=api.example.com # Deploy with custom domain
    $0 --destroy                    # Destroy current environment

ENVIRONMENT VARIABLES:
    AUTO_APPROVE=true              # Same as --auto-approve
    SKIP_BUILD=true               # Same as --skip-build
    DOMAIN_NAME=api.example.com   # Same as --domain
    ENABLE_HTTPS=false            # Same as --no-https

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-approve)
                AUTO_APPROVE="true"
                shift
                ;;
            --skip-build)
                SKIP_BUILD="true"
                shift
                ;;
            --domain=*)
                DOMAIN_NAME="${1#*=}"
                shift
                ;;
            --no-https)
                ENABLE_HTTPS="false"
                shift
                ;;
            --destroy)
                destroy_infrastructure
                exit 0
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            dev|prod)
                ENVIRONMENT="$1"
                shift
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("aws" "terraform" "docker" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log "ERROR" "Required tool not found: $tool"
            echo -e "${RED}Please install $tool and try again${NC}"
            exit 1
        fi
    done
    
    # Check AWS authentication
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log "ERROR" "AWS CLI not authenticated"
        echo -e "${RED}Please run 'aws configure' or set AWS credentials${NC}"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log "ERROR" "Docker daemon not running"
        echo -e "${RED}Please start Docker and try again${NC}"
        exit 1
    fi
    
    # Validate environment
    if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
        log "ERROR" "Invalid environment: $ENVIRONMENT"
        echo -e "${RED}Environment must be 'dev' or 'prod'${NC}"
        exit 1
    fi
    
    log "INFO" "Prerequisites check passed"
}

setup_directories() {
    log "INFO" "Setting up directories..."
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Verify terraform directory exists
    if [[ ! -d "$TERRAFORM_DIR" ]]; then
        log "ERROR" "Terraform directory not found: $TERRAFORM_DIR"
        exit 1
    fi
    
    log "INFO" "Directories setup complete"
}

setup_terraform() {
    log "INFO" "Setting up Terraform..."
    
    cd "$TERRAFORM_DIR"
    
    # Initialize Terraform
    log "INFO" "Initializing Terraform..."
    terraform init -input=false
    
    # Select or create workspace
    log "INFO" "Setting up workspace: $ENVIRONMENT"
    if terraform workspace select "$ENVIRONMENT" 2>/dev/null; then
        log "INFO" "Switched to existing workspace: $ENVIRONMENT"
    else
        log "INFO" "Creating new workspace: $ENVIRONMENT"
        terraform workspace new "$ENVIRONMENT"
    fi
    
    # Validate Terraform configuration
    log "INFO" "Validating Terraform configuration..."
    terraform validate
    
    log "INFO" "Terraform setup complete"
}

setup_variables() {
    log "INFO" "Setting up Terraform variables..."
    
    local tfvars_file="$TERRAFORM_DIR/terraform.${ENVIRONMENT}.tfvars"
    local tfvars_example="$TERRAFORM_DIR/terraform.tfvars.example"
    
    # Check if variables file exists
    if [[ ! -f "$tfvars_file" ]]; then
        if [[ -f "$tfvars_example" ]]; then
            log "WARN" "Variables file not found, creating from example..."
            cp "$tfvars_example" "$tfvars_file"
            
            # Update environment-specific values
            sed -i.bak "s/environment = \"dev\"/environment = \"$ENVIRONMENT\"/g" "$tfvars_file"
            
            if [[ -n "$DOMAIN_NAME" ]]; then
                sed -i.bak "s/domain_name = \"\"/domain_name = \"$DOMAIN_NAME\"/g" "$tfvars_file"
            fi
            
            if [[ "$ENABLE_HTTPS" == "false" ]]; then
                sed -i.bak "s/enable_https = true/enable_https = false/g" "$tfvars_file"
            fi
            
            rm -f "$tfvars_file.bak"
            
            log "WARN" "Please review and update variables in: $tfvars_file"
            log "WARN" "Press Enter to continue or Ctrl+C to abort..."
            read -r
        else
            log "ERROR" "No variables file found and no example available"
            exit 1
        fi
    fi
    
    log "INFO" "Variables setup complete"
}

build_and_push_images() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        log "INFO" "Skipping Docker build (SKIP_BUILD=true)"
        return 0
    fi
    
    log "INFO" "Building and pushing Docker images..."
    
    # Get AWS account ID and region
    local aws_account_id
    aws_account_id=$(aws sts get-caller-identity --query Account --output text)
    local aws_region
    aws_region=$(aws configure get region || echo "us-east-1")
    
    # ECR repository names
    local backend_repo="smart-0dte-backend"
    local frontend_repo="smart-0dte-frontend"
    
    # Login to ECR
    log "INFO" "Logging in to ECR..."
    aws ecr get-login-password --region "$aws_region" | \
        docker login --username AWS --password-stdin "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com"
    
    # Build and push backend
    log "INFO" "Building backend image..."
    docker build -t "$backend_repo:latest" -f backend/Dockerfile backend/
    docker tag "$backend_repo:latest" "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$backend_repo:latest"
    docker tag "$backend_repo:latest" "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$backend_repo:$TIMESTAMP"
    
    log "INFO" "Pushing backend image..."
    docker push "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$backend_repo:latest"
    docker push "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$backend_repo:$TIMESTAMP"
    
    # Build and push frontend
    log "INFO" "Building frontend image..."
    docker build -t "$frontend_repo:latest" -f smart-0dte-frontend/Dockerfile smart-0dte-frontend/
    docker tag "$frontend_repo:latest" "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$frontend_repo:latest"
    docker tag "$frontend_repo:latest" "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$frontend_repo:$TIMESTAMP"
    
    log "INFO" "Pushing frontend image..."
    docker push "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$frontend_repo:latest"
    docker push "$aws_account_id.dkr.ecr.$aws_region.amazonaws.com/$frontend_repo:$TIMESTAMP"
    
    log "INFO" "Docker images built and pushed successfully"
}

deploy_infrastructure() {
    log "INFO" "Deploying infrastructure..."
    
    cd "$TERRAFORM_DIR"
    
    # Create terraform plan
    log "INFO" "Creating Terraform plan..."
    terraform plan -var-file="terraform.${ENVIRONMENT}.tfvars" -out=tfplan
    
    # Apply terraform plan
    if [[ "$AUTO_APPROVE" == "true" ]]; then
        log "INFO" "Applying Terraform plan (auto-approved)..."
        terraform apply -auto-approve tfplan
    else
        log "INFO" "Applying Terraform plan (interactive)..."
        terraform apply tfplan
    fi
    
    log "INFO" "Infrastructure deployment complete"
}

get_deployment_outputs() {
    log "INFO" "Retrieving deployment outputs..."
    
    cd "$TERRAFORM_DIR"
    
    # Get Terraform outputs
    local app_url
    app_url=$(terraform output -raw app_url 2>/dev/null || echo "")
    local alb_dns
    alb_dns=$(terraform output -raw alb_dns 2>/dev/null || echo "")
    local rds_endpoint
    rds_endpoint=$(terraform output -raw rds_endpoint 2>/dev/null || echo "")
    local redis_endpoint
    redis_endpoint=$(terraform output -raw redis_endpoint 2>/dev/null || echo "")
    
    # Store outputs for later use
    export APP_URL="$app_url"
    export ALB_DNS="$alb_dns"
    export RDS_ENDPOINT="$rds_endpoint"
    export REDIS_ENDPOINT="$redis_endpoint"
    
    log "INFO" "Deployment outputs retrieved"
}

wait_for_readiness() {
    if [[ -z "${APP_URL:-}" ]]; then
        log "WARN" "No APP_URL available, skipping readiness check"
        return 0
    fi
    
    log "INFO" "Waiting for application readiness..."
    
    local max_attempts=40
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "DEBUG" "Readiness check attempt $attempt/$max_attempts"
        
        if curl -fsS --max-time 10 "$APP_URL/readyz" >/dev/null 2>&1; then
            log "INFO" "Application is ready!"
            return 0
        fi
        
        if curl -fsS --max-time 10 "$APP_URL/livez" >/dev/null 2>&1; then
            log "DEBUG" "Application is alive, waiting for readiness..."
        else
            log "DEBUG" "Application not responding yet..."
        fi
        
        sleep 15
        ((attempt++))
    done
    
    log "ERROR" "Application failed to become ready within $(($max_attempts * 15)) seconds"
    log "ERROR" "Check application logs and health endpoints"
    return 1
}

run_smoke_tests() {
    if [[ -z "${APP_URL:-}" ]]; then
        log "WARN" "No APP_URL available, skipping smoke tests"
        return 0
    fi
    
    log "INFO" "Running smoke tests..."
    
    local tests_passed=0
    local tests_total=0
    
    # Test health endpoint
    ((tests_total++))
    if curl -fsS "$APP_URL/health" >/dev/null 2>&1; then
        log "INFO" "✓ Health endpoint test passed"
        ((tests_passed++))
    else
        log "ERROR" "✗ Health endpoint test failed"
    fi
    
    # Test readiness endpoint
    ((tests_total++))
    if curl -fsS "$APP_URL/readyz" >/dev/null 2>&1; then
        log "INFO" "✓ Readiness endpoint test passed"
        ((tests_passed++))
    else
        log "ERROR" "✗ Readiness endpoint test failed"
    fi
    
    # Test API endpoint
    ((tests_total++))
    if curl -fsS "$APP_URL/api/v1/market-data/status" >/dev/null 2>&1; then
        log "INFO" "✓ API endpoint test passed"
        ((tests_passed++))
    else
        log "ERROR" "✗ API endpoint test failed"
    fi
    
    log "INFO" "Smoke tests completed: $tests_passed/$tests_total passed"
    
    if [[ $tests_passed -eq $tests_total ]]; then
        return 0
    else
        return 1
    fi
}

show_deployment_summary() {
    log "INFO" "Deployment Summary"
    echo
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo
    echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
    echo -e "${BLUE}Timestamp:${NC} $TIMESTAMP"
    echo
    
    if [[ -n "${APP_URL:-}" ]]; then
        echo -e "${BLUE}Application URL:${NC} $APP_URL"
        echo -e "${BLUE}Health Check:${NC} $APP_URL/health"
        echo -e "${BLUE}Readiness Check:${NC} $APP_URL/readyz"
        echo -e "${BLUE}API Documentation:${NC} $APP_URL/docs"
    fi
    
    if [[ -n "${ALB_DNS:-}" ]]; then
        echo -e "${BLUE}Load Balancer:${NC} $ALB_DNS"
    fi
    
    if [[ -n "${RDS_ENDPOINT:-}" ]]; then
        echo -e "${BLUE}Database:${NC} $RDS_ENDPOINT"
    fi
    
    if [[ -n "${REDIS_ENDPOINT:-}" ]]; then
        echo -e "${BLUE}Redis:${NC} $REDIS_ENDPOINT"
    fi
    
    echo
    echo -e "${BLUE}Logs:${NC} $LOG_FILE"
    echo
    echo -e "${GREEN}Your Smart-0DTE-System is now running in the cloud!${NC}"
}

destroy_infrastructure() {
    log "WARN" "Destroying infrastructure for environment: $ENVIRONMENT"
    
    cd "$TERRAFORM_DIR"
    
    # Select workspace
    terraform workspace select "$ENVIRONMENT" 2>/dev/null || {
        log "ERROR" "Workspace $ENVIRONMENT not found"
        exit 1
    }
    
    # Confirm destruction
    if [[ "$AUTO_APPROVE" != "true" ]]; then
        echo -e "${RED}⚠ This will destroy all resources in the $ENVIRONMENT environment${NC}"
        echo -e "${RED}⚠ This action cannot be undone${NC}"
        echo
        read -p "Type 'yes' to confirm destruction: " confirmation
        
        if [[ "$confirmation" != "yes" ]]; then
            log "INFO" "Destruction cancelled"
            exit 0
        fi
    fi
    
    # Destroy infrastructure
    log "INFO" "Destroying infrastructure..."
    terraform destroy -var-file="terraform.${ENVIRONMENT}.tfvars" -auto-approve
    
    log "INFO" "Infrastructure destroyed successfully"
}

main() {
    echo -e "${BLUE}Smart-0DTE-System Cloud Deployment${NC}"
    echo -e "${BLUE}===================================${NC}"
    echo
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Setup and checks
    setup_directories
    check_prerequisites
    
    log "INFO" "Starting deployment to $ENVIRONMENT environment"
    
    # Deployment steps
    setup_terraform
    setup_variables
    build_and_push_images
    deploy_infrastructure
    get_deployment_outputs
    wait_for_readiness
    
    # Validation
    if run_smoke_tests; then
        show_deployment_summary
        log "INFO" "Deployment completed successfully"
        exit 0
    else
        log "ERROR" "Deployment completed but smoke tests failed"
        log "ERROR" "Please check the application manually"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"

