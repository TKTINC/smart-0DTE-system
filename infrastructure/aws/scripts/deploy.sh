#!/bin/bash

# Smart-0DTE-System AWS Deployment Script
# This script deploys the complete Smart-0DTE-System infrastructure to AWS

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure/aws"

# Default values
ENVIRONMENT="production"
REGION="us-east-1"
STACK_NAME="smart-0dte-system"
DOMAIN_NAME=""
CERTIFICATE_ARN=""
NOTIFICATION_EMAIL=""
KEY_PAIR_NAME=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Smart-0DTE-System AWS Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENVIRONMENT    Environment (development|staging|production) [default: production]
    -r, --region REGION             AWS region [default: us-east-1]
    -s, --stack-name STACK_NAME     CloudFormation stack name [default: smart-0dte-system]
    -d, --domain DOMAIN             Domain name for the application
    -c, --certificate-arn ARN       SSL certificate ARN
    -n, --notification-email EMAIL  Email for CloudWatch notifications
    -k, --key-pair KEY_PAIR         EC2 key pair name
    --validate-only                 Only validate the CloudFormation template
    --dry-run                       Show what would be deployed without executing
    -h, --help                      Show this help message

EXAMPLES:
    # Deploy to production
    $0 -e production -d smart0dte.com -c arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012 -n admin@smart0dte.com -k my-key-pair

    # Deploy to staging
    $0 -e staging -d staging.smart0dte.com -c arn:aws:acm:us-east-1:123456789012:certificate/87654321-4321-4321-4321-210987654321 -n admin@smart0dte.com

    # Validate template only
    $0 --validate-only

PREREQUISITES:
    - AWS CLI configured with appropriate permissions
    - Docker installed (for building container images)
    - Valid SSL certificate in AWS Certificate Manager
    - Domain name configured in Route 53 (optional)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN_NAME="$2"
            shift 2
            ;;
        -c|--certificate-arn)
            CERTIFICATE_ARN="$2"
            shift 2
            ;;
        -n|--notification-email)
            NOTIFICATION_EMAIL="$2"
            shift 2
            ;;
        -k|--key-pair)
            KEY_PAIR_NAME="$2"
            shift 2
            ;;
        --validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Must be development, staging, or production."
    exit 1
fi

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi

    # Validate required parameters for non-validation runs
    if [[ "$VALIDATE_ONLY" != true ]]; then
        if [[ -z "$DOMAIN_NAME" ]]; then
            log_error "Domain name is required. Use -d or --domain option."
            exit 1
        fi

        if [[ -z "$CERTIFICATE_ARN" ]]; then
            log_error "SSL certificate ARN is required. Use -c or --certificate-arn option."
            exit 1
        fi

        if [[ -z "$NOTIFICATION_EMAIL" ]]; then
            log_error "Notification email is required. Use -n or --notification-email option."
            exit 1
        fi

        if [[ -z "$KEY_PAIR_NAME" ]]; then
            log_warning "No key pair specified. EC2 instances (if any) will not be accessible via SSH."
            KEY_PAIR_NAME="dummy-key-pair"
        fi
    fi

    log_success "Prerequisites check passed"
}

# Validate CloudFormation template
validate_template() {
    log_info "Validating CloudFormation template..."
    
    local template_file="$INFRASTRUCTURE_DIR/cloudformation/smart-0dte-infrastructure.yaml"
    
    if [[ ! -f "$template_file" ]]; then
        log_error "CloudFormation template not found: $template_file"
        exit 1
    fi

    if aws cloudformation validate-template --template-body "file://$template_file" --region "$REGION" &> /dev/null; then
        log_success "CloudFormation template is valid"
    else
        log_error "CloudFormation template validation failed"
        aws cloudformation validate-template --template-body "file://$template_file" --region "$REGION"
        exit 1
    fi
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building and pushing Docker image..."

    # Get AWS account ID
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local ecr_uri="${account_id}.dkr.ecr.${REGION}.amazonaws.com"
    local repository_name="${STACK_NAME}-backend"
    local image_tag="latest"

    # Create ECR repository if it doesn't exist
    if ! aws ecr describe-repositories --repository-names "$repository_name" --region "$REGION" &> /dev/null; then
        log_info "Creating ECR repository: $repository_name"
        aws ecr create-repository --repository-name "$repository_name" --region "$REGION" > /dev/null
    fi

    # Get ECR login token
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ecr_uri"

    # Build Docker image
    log_info "Building Docker image..."
    cd "$PROJECT_ROOT/backend"
    docker build -t "$repository_name:$image_tag" .

    # Tag image for ECR
    docker tag "$repository_name:$image_tag" "$ecr_uri/$repository_name:$image_tag"

    # Push image to ECR
    log_info "Pushing image to ECR..."
    docker push "$ecr_uri/$repository_name:$image_tag"

    log_success "Docker image built and pushed successfully"
}

# Deploy CloudFormation stack
deploy_stack() {
    log_info "Deploying CloudFormation stack: $STACK_NAME"

    local template_file="$INFRASTRUCTURE_DIR/cloudformation/smart-0dte-infrastructure.yaml"
    local parameters_file="$INFRASTRUCTURE_DIR/configs/parameters-${ENVIRONMENT}.json"

    # Create parameters file if it doesn't exist
    if [[ ! -f "$parameters_file" ]]; then
        log_info "Creating parameters file: $parameters_file"
        mkdir -p "$(dirname "$parameters_file")"
        cat > "$parameters_file" << EOF
[
    {
        "ParameterKey": "Environment",
        "ParameterValue": "$ENVIRONMENT"
    },
    {
        "ParameterKey": "DomainName",
        "ParameterValue": "$DOMAIN_NAME"
    },
    {
        "ParameterKey": "CertificateArn",
        "ParameterValue": "$CERTIFICATE_ARN"
    },
    {
        "ParameterKey": "NotificationEmail",
        "ParameterValue": "$NOTIFICATION_EMAIL"
    },
    {
        "ParameterKey": "KeyPairName",
        "ParameterValue": "$KEY_PAIR_NAME"
    },
    {
        "ParameterKey": "DatabasePassword",
        "ParameterValue": "$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)"
    }
]
EOF
    fi

    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
        log_info "Stack exists. Updating..."
        local action="update-stack"
    else
        log_info "Stack does not exist. Creating..."
        local action="create-stack"
    fi

    # Deploy stack
    local stack_id
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would execute:"
        echo "aws cloudformation $action --stack-name $STACK_NAME --template-body file://$template_file --parameters file://$parameters_file --capabilities CAPABILITY_NAMED_IAM --region $REGION"
        return 0
    fi

    stack_id=$(aws cloudformation "$action" \
        --stack-name "$STACK_NAME" \
        --template-body "file://$template_file" \
        --parameters "file://$parameters_file" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region "$REGION" \
        --query 'StackId' \
        --output text)

    log_info "Stack deployment initiated. Stack ID: $stack_id"

    # Wait for stack deployment to complete
    log_info "Waiting for stack deployment to complete..."
    if [[ "$action" == "create-stack" ]]; then
        aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"
    else
        aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION"
    fi

    # Check deployment status
    local stack_status=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text)
    
    if [[ "$stack_status" =~ COMPLETE$ ]]; then
        log_success "Stack deployment completed successfully"
    else
        log_error "Stack deployment failed with status: $stack_status"
        exit 1
    fi
}

# Deploy ECS service
deploy_ecs_service() {
    log_info "Deploying ECS service..."

    # Get stack outputs
    local cluster_name=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' --output text)
    local target_group_arn=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`ALBTargetGroupArn`].OutputValue' --output text 2>/dev/null || echo "")
    local ecr_uri=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryURI`].OutputValue' --output text)

    # Create task definition
    local task_definition_file="$INFRASTRUCTURE_DIR/configs/task-definition-${ENVIRONMENT}.json"
    
    if [[ ! -f "$task_definition_file" ]]; then
        log_info "Creating ECS task definition..."
        mkdir -p "$(dirname "$task_definition_file")"
        
        # Get environment-specific values
        local cpu_value memory_value
        case "$ENVIRONMENT" in
            development)
                cpu_value=256
                memory_value=512
                ;;
            staging)
                cpu_value=512
                memory_value=1024
                ;;
            production)
                cpu_value=1024
                memory_value=2048
                ;;
        esac

        cat > "$task_definition_file" << EOF
{
    "family": "${STACK_NAME}-backend",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "$cpu_value",
    "memory": "$memory_value",
    "executionRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/${STACK_NAME}-ecs-execution-role",
    "taskRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/${STACK_NAME}-ecs-task-role",
    "containerDefinitions": [
        {
            "name": "backend",
            "image": "${ecr_uri}:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/${STACK_NAME}",
                    "awslogs-region": "$REGION",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "environment": [
                {
                    "name": "ENVIRONMENT",
                    "value": "$ENVIRONMENT"
                },
                {
                    "name": "AWS_REGION",
                    "value": "$REGION"
                }
            ],
            "secrets": [
                {
                    "name": "DATABASE_URL",
                    "valueFrom": "arn:aws:secretsmanager:$REGION:$(aws sts get-caller-identity --query Account --output text):secret:${STACK_NAME}/database"
                }
            ]
        }
    ]
}
EOF
    fi

    # Register task definition
    log_info "Registering ECS task definition..."
    local task_definition_arn=$(aws ecs register-task-definition \
        --cli-input-json "file://$task_definition_file" \
        --region "$REGION" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)

    log_success "Task definition registered: $task_definition_arn"

    # Create or update ECS service
    local service_name="${STACK_NAME}-backend-service"
    
    if aws ecs describe-services --cluster "$cluster_name" --services "$service_name" --region "$REGION" &> /dev/null; then
        log_info "Updating ECS service..."
        aws ecs update-service \
            --cluster "$cluster_name" \
            --service "$service_name" \
            --task-definition "$task_definition_arn" \
            --region "$REGION" > /dev/null
    else
        log_info "Creating ECS service..."
        
        # Get VPC and subnet information
        local vpc_id=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`VPCId`].OutputValue' --output text)
        local private_subnets=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" "Name=tag:Name,Values=*private*" --query 'Subnets[].SubnetId' --output text --region "$REGION" | tr '\t' ',')
        local security_group=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$vpc_id" "Name=group-name,Values=${STACK_NAME}-ecs-sg" --query 'SecurityGroups[0].GroupId' --output text --region "$REGION")

        aws ecs create-service \
            --cluster "$cluster_name" \
            --service-name "$service_name" \
            --task-definition "$task_definition_arn" \
            --desired-count 2 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$private_subnets],securityGroups=[$security_group],assignPublicIp=DISABLED}" \
            --load-balancers "targetGroupArn=$target_group_arn,containerName=backend,containerPort=8000" \
            --region "$REGION" > /dev/null
    fi

    log_success "ECS service deployed successfully"
}

# Get deployment outputs
get_outputs() {
    log_info "Retrieving deployment outputs..."

    echo ""
    echo "=== DEPLOYMENT OUTPUTS ==="
    
    # Get stack outputs
    aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' --output table

    echo ""
    echo "=== ACCESS INFORMATION ==="
    
    local alb_dns=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text)
    local cloudfront_domain=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomain`].OutputValue' --output text)

    echo "Application Load Balancer: https://$alb_dns"
    echo "CloudFront Distribution: https://$cloudfront_domain"
    
    if [[ -n "$DOMAIN_NAME" ]]; then
        echo "Custom Domain: https://$DOMAIN_NAME"
    fi

    echo ""
    echo "=== NEXT STEPS ==="
    echo "1. Update your DNS records to point to the CloudFront distribution"
    echo "2. Monitor the ECS service deployment in the AWS Console"
    echo "3. Check CloudWatch logs for any application errors"
    echo "4. Run health checks to verify the deployment"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    # Add any cleanup logic here
}

# Main execution
main() {
    log_info "Starting Smart-0DTE-System AWS deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $REGION"
    log_info "Stack Name: $STACK_NAME"

    # Set trap for cleanup
    trap cleanup EXIT

    # Check prerequisites
    check_prerequisites

    # Validate template
    validate_template

    # Exit if validation only
    if [[ "$VALIDATE_ONLY" == true ]]; then
        log_success "Template validation completed successfully"
        exit 0
    fi

    # Build and push Docker image
    if [[ "$DRY_RUN" != true ]]; then
        build_and_push_image
    fi

    # Deploy CloudFormation stack
    deploy_stack

    # Deploy ECS service
    if [[ "$DRY_RUN" != true ]]; then
        deploy_ecs_service
    fi

    # Get outputs
    if [[ "$DRY_RUN" != true ]]; then
        get_outputs
    fi

    log_success "Deployment completed successfully!"
}

# Run main function
main "$@"

