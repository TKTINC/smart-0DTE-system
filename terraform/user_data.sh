#!/bin/bash

# Smart-0DTE-System EC2 User Data Script
# This script sets up the application on EC2 instances

set -e

# Update system
yum update -y

# Install Docker
amazon-linux-extras install docker -y
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Git
yum install -y git

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create application directory
mkdir -p /opt/smart-0dte-system
cd /opt/smart-0dte-system

# Clone repository (in production, you'd use a specific release)
git clone https://github.com/TKTINC/smart-0DTE-system.git .

# Create environment file
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
REDIS_URL=redis://${redis_host}:6379

# API Keys
POLYGON_API_KEY=${polygon_api_key}
ALPHA_VANTAGE_API_KEY=${alpha_vantage_api_key}
OPENAI_API_KEY=${openai_api_key}

# IBKR Configuration
IBKR_HOST=${ibkr_host}
IBKR_PORT=${ibkr_port}
IBKR_CLIENT_ID=${ibkr_client_id}

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

# Create production Docker Compose override
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  backend:
    environment:
      - DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
      - REDIS_URL=redis://${redis_host}:6379
    restart: always
    
  data-feed:
    environment:
      - DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
      - REDIS_URL=redis://${redis_host}:6379
    restart: always
    
  signal-generator:
    environment:
      - DATABASE_URL=postgresql://postgres:${db_password}@${db_host}:5432/${db_name}
      - REDIS_URL=redis://${redis_host}:6379
    restart: always
    
  frontend:
    restart: always

# Remove database services (using managed services)
  postgres:
    deploy:
      replicas: 0
      
  redis:
    deploy:
      replicas: 0
      
  influxdb:
    deploy:
      replicas: 0
EOF

# Build and start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Create systemd service for auto-start
cat > /etc/systemd/system/smart-0dte.service << EOF
[Unit]
Description=Smart-0DTE-System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/smart-0dte-system
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl enable smart-0dte.service

# Configure CloudWatch logging
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/smart-0dte-system/logs/*.log",
            "log_group_name": "/aws/ec2/smart-0dte-system",
            "log_stream_name": "{instance_id}/application"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Create health check script
cat > /opt/smart-0dte-system/health-check.sh << 'EOF'
#!/bin/bash
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:3000 || exit 1
EOF

chmod +x /opt/smart-0dte-system/health-check.sh

# Add health check to cron
echo "*/5 * * * * /opt/smart-0dte-system/health-check.sh" | crontab -

# Signal completion
/opt/aws/bin/cfn-signal -e $? --stack "$${AWS::StackName}" --resource AutoScalingGroup --region "$${AWS::Region}" || true

