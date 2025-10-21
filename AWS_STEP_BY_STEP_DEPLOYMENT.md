# 🚀 AWS Step-by-Step Deployment Guide

Complete guide for deploying the Crypto Data Collection System on AWS with CI/CD, auto-deployment, and parallel services.

## 📋 Prerequisites Checklist

- [ ] AWS Account with console access
- [ ] GitHub repository created
- [ ] AWS CLI installed and configured
- [ ] Docker installed locally
- [ ] Domain name (optional, for custom domain)

## 🎯 Step 1: AWS CLI Setup

### 1.1 Install AWS CLI
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install awscli

# macOS
brew install awscli

# Windows
# Download from: https://aws.amazon.com/cli/
```

### 1.2 Configure AWS CLI
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (us-east-1)
# Enter your default output format (json)
```

### 1.3 Verify Configuration
```bash
aws sts get-caller-identity
# Should return your AWS account information
```

## 🏗️ Step 2: Infrastructure Setup

### 2.1 Run Infrastructure Setup Script
```bash
# Make script executable
chmod +x scripts/setup-aws-infrastructure.sh

# Run the setup script
./scripts/setup-aws-infrastructure.sh
```

This script will create:
- ECR repository for Docker images
- ECS cluster for container orchestration
- VPC with subnets and internet gateway
- Security groups
- CloudWatch log groups
- ECS task definition
- ECS service

### 2.2 Verify Infrastructure
```bash
# Check ECR repository
aws ecr describe-repositories --repository-names crypto-data-api

# Check ECS cluster
aws ecs describe-clusters --clusters crypto-data-cluster

# Check VPC
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=crypto-data-vpc"
```

## 🐳 Step 3: Docker Image Build and Push

### 3.1 Build Docker Image
```bash
# Build the image
docker build -t crypto-data-api .

# Test the image locally
docker run -p 5001:5001 crypto-data-api
```

### 3.2 Push to ECR
```bash
# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push image
docker tag crypto-data-api:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest
```

## 🔄 Step 4: GitHub Repository Setup

### 4.1 Create GitHub Repository
1. Go to GitHub.com
2. Click "New repository"
3. Name: `crypto-data-collection`
4. Make it public or private
5. Don't initialize with README (we have files already)

### 4.2 Push Code to GitHub
```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit: Crypto data collection system"

# Add remote origin
git remote add origin https://github.com/YOUR_USERNAME/crypto-data-collection.git

# Push to GitHub
git push -u origin main
```

### 4.3 Add GitHub Secrets
1. Go to your GitHub repository
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add these secrets:

```
AWS_ACCESS_KEY_ID: your-aws-access-key
AWS_SECRET_ACCESS_KEY: your-aws-secret-key
MONGODB_URL: mongodb://your-mongodb-connection-string
MONGODB_DATABASE: crypto_trading_data
```

## 🚀 Step 5: Deploy to AWS

### 5.1 Run Complete Deployment
```bash
# Make deployment script executable
chmod +x scripts/deploy-to-aws.sh

# Run complete deployment
./scripts/deploy-to-aws.sh
```

This script will:
- Setup all AWS infrastructure
- Build and push Docker image
- Update ECS task definition
- Deploy ECS service
- Create Lambda function for historical data
- Create API Gateway
- Run health checks

### 5.2 Verify Deployment
```bash
# Check ECS service status
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# Check service logs
aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id
```

## 📊 Step 6: Test the Deployment

### 6.1 Get Service URL
```bash
# Get public IP of the service
aws ecs describe-tasks --cluster crypto-data-cluster --tasks $(aws ecs list-tasks --cluster crypto-data-cluster --service-name crypto-api-service --query 'taskArns[0]' --output text)
```

### 6.2 Test API Endpoints
```bash
# Replace YOUR_PUBLIC_IP with the actual IP
export API_URL="http://YOUR_PUBLIC_IP:5001"

# Test health endpoint
curl $API_URL/health

# Test real-time data
curl $API_URL/realtime

# Test exchanges
curl $API_URL/exchanges

# Test symbols
curl $API_URL/symbols
```

## 🔄 Step 7: CI/CD Pipeline

### 7.1 GitHub Actions Workflow
The `.github/workflows/deploy.yml` file is already configured to:
- Run tests on pull requests
- Build and deploy on main branch pushes
- Update ECS service automatically

### 7.2 Test CI/CD
```bash
# Make a small change
echo "# Test change" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin main

# Check GitHub Actions tab for deployment status
```

## 📈 Step 8: Monitoring and Management

### 8.1 CloudWatch Monitoring
```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard --dashboard-name "Crypto-Data-Dashboard" --dashboard-body file://cloudwatch-dashboard.json
```

### 8.2 Health Monitoring
```bash
# Check detailed health
curl $API_URL/health/detailed

# Monitor logs
aws logs tail /ecs/crypto-api --follow
```

### 8.3 Service Management
```bash
# Scale service
aws ecs update-service --cluster crypto-data-cluster --service crypto-api-service --desired-count 2

# Update service
aws ecs update-service --cluster crypto-data-cluster --service crypto-api-service --force-new-deployment

# Stop service
aws ecs update-service --cluster crypto-data-cluster --service crypto-api-service --desired-count 0
```

## 📊 Step 9: Historical Data Collection

### 9.1 On-Demand Collection
```bash
# Trigger historical collection via Lambda
curl -X POST https://YOUR_API_GATEWAY_URL/prod/historical \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2021-01-01",
    "end_date": "2024-12-31",
    "exchanges": ["binance", "bybit", "kraken", "gate"],
    "symbols": ["BTCUSDT", "BTCUSDC", "BTCBUSD"],
    "timeframes": ["1m", "1h"]
  }'
```

### 9.2 Scheduled Collection
```bash
# Create CloudWatch Events rule for scheduled collection
aws events put-rule --name crypto-historical-collection --schedule-expression "rate(1 day)"
aws events put-targets --rule crypto-historical-collection --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:crypto-historical-collection"
```

## 🔧 Step 10: Production Optimization

### 10.1 Auto Scaling
```bash
# Create auto scaling target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/crypto-data-cluster/crypto-api-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10
```

### 10.2 Load Balancer
```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name crypto-data-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx
```

### 10.3 SSL Certificate
```bash
# Request SSL certificate
aws acm request-certificate \
  --domain-name your-domain.com \
  --validation-method DNS
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. ECS Service Not Starting
```bash
# Check service events
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# Check task logs
aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id
```

#### 2. Database Connection Issues
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Test connectivity
aws ecs run-task --cluster crypto-data-cluster --task-definition crypto-api-task
```

#### 3. GitHub Actions Failing
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify ECR permissions
aws ecr describe-repositories --repository-names crypto-data-api
```

#### 4. API Not Responding
```bash
# Check if service is running
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# Check health endpoint
curl http://YOUR_PUBLIC_IP:5001/health

# Check logs
aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id
```

## 📞 Support and Maintenance

### Daily Operations
```bash
# Check service status
./scripts/status-check.sh

# Monitor logs
aws logs tail /ecs/crypto-api --follow

# Check health
curl $API_URL/health/detailed
```

### Weekly Maintenance
```bash
# Update service
aws ecs update-service --cluster crypto-data-cluster --service crypto-api-service --force-new-deployment

# Check resource usage
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name CPUUtilization --dimensions Name=ServiceName,Value=crypto-api-service --start-time 2024-01-01T00:00:00Z --end-time 2024-01-07T23:59:59Z --period 3600 --statistics Average
```

### Monthly Review
- Review CloudWatch metrics
- Check cost optimization
- Update security groups
- Review access logs
- Backup database

## 🎉 Success Checklist

- [ ] AWS infrastructure created
- [ ] Docker image built and pushed
- [ ] GitHub repository configured
- [ ] CI/CD pipeline working
- [ ] ECS service running
- [ ] API endpoints responding
- [ ] Real-time data collection working
- [ ] Historical data collection available
- [ ] Monitoring configured
- [ ] Health checks passing

## 🚀 Next Steps

1. **Custom Domain**: Set up Route 53 and SSL certificate
2. **Monitoring**: Configure CloudWatch alarms and notifications
3. **Backup**: Set up automated database backups
4. **Security**: Review and update security groups
5. **Scaling**: Configure auto-scaling policies
6. **Cost Optimization**: Review and optimize costs

---

## 📞 Quick Commands Reference

```bash
# Check service status
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# View logs
aws logs tail /ecs/crypto-api --follow

# Update service
aws ecs update-service --cluster crypto-data-cluster --service crypto-api-service --force-new-deployment

# Scale service
aws ecs update-service --cluster crypto-data-cluster --service crypto-api-service --desired-count 2

# Test API
curl http://YOUR_PUBLIC_IP:5001/health

# Trigger historical collection
curl -X POST https://YOUR_API_GATEWAY_URL/prod/historical
```

Your AWS deployment is now complete! 🎉
