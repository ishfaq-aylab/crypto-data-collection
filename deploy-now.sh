#!/bin/bash
# Deploy Now - Step by Step Script
# ================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploy Your Crypto Data Collection System to AWS${NC}"
echo "======================================================"

# Step 1: Initialize Git
echo -e "${BLUE}📝 Step 1: Initialize Git Repository${NC}"
echo "----------------------------------------"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Git not initialized. Initializing...${NC}"
    git init
    echo -e "${GREEN}✅ Git initialized${NC}"
else
    echo -e "${GREEN}✅ Git already initialized${NC}"
fi

# Add .gitignore first
echo -e "${BLUE}📝 Adding .gitignore file...${NC}"
git add .gitignore

# Add all files (respecting .gitignore)
echo -e "${BLUE}📦 Adding project files to git (excluding venv, cache, logs)...${NC}"
git add .

# Check what files are staged
echo -e "${BLUE}📋 Files to be committed:${NC}"
git diff --staged --name-only

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo -e "${YELLOW}⚠️  No changes to commit${NC}"
else
    git commit -m "Initial commit: Crypto data collection system with AWS deployment"
    echo -e "${GREEN}✅ Files committed${NC}"
fi

# Step 2: Check AWS CLI
echo -e "${BLUE}🔧 Step 2: Check AWS CLI Configuration${NC}"
echo "----------------------------------------"

if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured. Please run 'aws configure' first.${NC}"
    echo -e "${YELLOW}💡 Run: aws configure${NC}"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS CLI configured${NC}"
echo -e "${BLUE}📊 AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# Step 3: Check Docker
echo -e "${BLUE}🐳 Step 3: Check Docker${NC}"
echo "----------------------------------------"

if ! docker --version > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker installed and running${NC}"

# Step 4: Deploy to AWS
echo -e "${BLUE}🚀 Step 4: Deploy to AWS${NC}"
echo "----------------------------------------"

echo -e "${BLUE}🏗️  Setting up AWS infrastructure...${NC}"
./scripts/setup-aws-infrastructure.sh

echo -e "${BLUE}🐳 Building and pushing Docker image...${NC}"

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t crypto-data-api .

# Tag and push image
docker tag crypto-data-api:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest

echo -e "${BLUE}📋 Updating task definition...${NC}"
sed -i "s/ACCOUNT/$AWS_ACCOUNT_ID/g" ecs-task-definition.json
sed -i "s/us-east-1/us-east-1/g" ecs-task-definition.json

# Register new task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json --region us-east-1

echo -e "${BLUE}🚀 Updating ECS service...${NC}"
aws ecs update-service \
    --cluster crypto-data-cluster \
    --service crypto-api-service \
    --task-definition crypto-api-task \
    --force-new-deployment \
    --region us-east-1

echo -e "${BLUE}⏳ Waiting for service to be stable...${NC}"
aws ecs wait services-stable \
    --cluster crypto-data-cluster \
    --services crypto-api-service \
    --region us-east-1

# Get Public IP
echo -e "${BLUE}🌐 Getting public IP...${NC}"
SERVICE_INFO=$(aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service --region us-east-1)
TASK_ARN=$(echo $SERVICE_INFO | jq -r '.services[0].taskSets[0].taskSetId')

TASK_INFO=$(aws ecs describe-tasks --cluster crypto-data-cluster --tasks $TASK_ARN --region us-east-1)
PUBLIC_IP=$(echo $TASK_INFO | jq -r '.tasks[0].attachments[0].details[] | select(.name=="networkInterfaceId") | .value' | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region us-east-1)

echo -e "${BLUE}🔍 Running health check...${NC}"
sleep 30  # Wait for service to start

if curl -f http://$PUBLIC_IP:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo -e "${BLUE}🌐 API Server URL: http://$PUBLIC_IP:5001${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed - service may still be starting${NC}"
fi

# Step 5: GitHub Setup Instructions
echo -e "${BLUE}📝 Step 5: GitHub Setup Instructions${NC}"
echo "----------------------------------------"
echo -e "${YELLOW}📋 Next steps for GitHub setup:${NC}"
echo ""
echo -e "${BLUE}1. Create GitHub Repository:${NC}"
echo -e "   - Go to https://github.com"
echo -e "   - Click 'New repository'"
echo -e "   - Name: crypto-data-collection"
echo -e "   - Make it Public"
echo -e "   - Don't initialize with README"
echo -e "   - Click 'Create repository'"
echo ""
echo -e "${BLUE}2. Connect Local Repository:${NC}"
echo -e "   git remote add origin https://github.com/YOUR_USERNAME/crypto-data-collection.git"
echo -e "   git push -u origin main"
echo ""
echo -e "${BLUE}3. Add GitHub Secrets:${NC}"
echo -e "   - Go to repository Settings → Secrets and variables → Actions"
echo -e "   - Add these secrets:"
echo -e "     - AWS_ACCESS_KEY_ID: $AWS_ACCOUNT_ID"
echo -e "     - AWS_SECRET_ACCESS_KEY: [Your secret key]"
echo -e "     - MONGODB_URL: mongodb://localhost:27017"
echo -e "     - MONGODB_DATABASE: model-collections"
echo ""

# Step 6: Test API
echo -e "${BLUE}🧪 Step 6: Test API Endpoints${NC}"
echo "----------------------------------------"

echo -e "${BLUE}Testing API endpoints...${NC}"

# Test health endpoint
echo -e "${BLUE}🔍 Testing health endpoint...${NC}"
if curl -f http://$PUBLIC_IP:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health endpoint working${NC}"
else
    echo -e "${RED}❌ Health endpoint failed${NC}"
fi

# Test real-time data
echo -e "${BLUE}🔍 Testing real-time data endpoint...${NC}"
if curl -f http://$PUBLIC_IP:5001/realtime > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Real-time data endpoint working${NC}"
else
    echo -e "${RED}❌ Real-time data endpoint failed${NC}"
fi

# Test exchanges
echo -e "${BLUE}🔍 Testing exchanges endpoint...${NC}"
if curl -f http://$PUBLIC_IP:5001/exchanges > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Exchanges endpoint working${NC}"
else
    echo -e "${RED}❌ Exchanges endpoint failed${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=================================="
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo -e "  AWS Account ID: $AWS_ACCOUNT_ID"
echo -e "  ECS Cluster: crypto-data-cluster"
echo -e "  ECS Service: crypto-api-service"
echo -e "  API Server URL: http://$PUBLIC_IP:5001"
echo ""
echo -e "${BLUE}🚀 Available Endpoints:${NC}"
echo -e "  Health Check: http://$PUBLIC_IP:5001/health"
echo -e "  Real-time Data: http://$PUBLIC_IP:5001/realtime"
echo -e "  Historical Data: http://$PUBLIC_IP:5001/historical"
echo -e "  Exchanges: http://$PUBLIC_IP:5001/exchanges"
echo -e "  Symbols: http://$PUBLIC_IP:5001/symbols"
echo ""
echo -e "${BLUE}📝 Next Steps:${NC}"
echo -e "  1. Set up GitHub repository (see instructions above)"
echo -e "  2. Add GitHub secrets for CI/CD"
echo -e "  3. Push code to trigger automatic deployment"
echo -e "  4. Monitor service health and logs"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo -e "  Check service status:"
echo -e "    aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service"
echo -e "  View logs:"
echo -e "    aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id"
echo -e "  Test API:"
echo -e "    curl http://$PUBLIC_IP:5001/health"
echo ""
echo -e "${GREEN}Your crypto data collection system is now running on AWS! 🎉${NC}"
