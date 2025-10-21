#!/bin/bash
# Complete AWS Deployment Script
# ==============================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Complete AWS Deployment for Crypto Data Collection${NC}"
echo "============================================================="

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="crypto-data-api"
ECS_CLUSTER="crypto-data-cluster"
ECS_SERVICE="crypto-api-service"
ECS_TASK_DEFINITION="crypto-api-task"

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check AWS CLI
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ AWS CLI configured${NC}"

# Check Docker
if ! docker --version > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker installed${NC}"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${BLUE}📊 AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# 1. Setup Infrastructure
echo -e "${BLUE}🏗️  Setting up AWS infrastructure...${NC}"
./scripts/setup-aws-infrastructure.sh

# 2. Build and Push Docker Image
echo -e "${BLUE}🐳 Building and pushing Docker image...${NC}"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
echo -e "${BLUE}📦 Building Docker image...${NC}"
docker build -t $ECR_REPOSITORY .

# Tag image
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Push image
echo -e "${BLUE}📤 Pushing image to ECR...${NC}"
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# 3. Update Task Definition
echo -e "${BLUE}📋 Updating task definition...${NC}"
sed -i "s/ACCOUNT/$AWS_ACCOUNT_ID/g" ecs-task-definition.json
sed -i "s/us-east-1/$AWS_REGION/g" ecs-task-definition.json

# Register new task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json --region $AWS_REGION

# 4. Update ECS Service
echo -e "${BLUE}🚀 Updating ECS service...${NC}"
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --task-definition $ECS_TASK_DEFINITION \
    --force-new-deployment \
    --region $AWS_REGION

# 5. Wait for Service to be Stable
echo -e "${BLUE}⏳ Waiting for service to be stable...${NC}"
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION

# 6. Get Service Information
echo -e "${BLUE}📊 Getting service information...${NC}"
SERVICE_INFO=$(aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION)
TASK_ARN=$(echo $SERVICE_INFO | jq -r '.services[0].taskSets[0].taskSetId')

# 7. Get Public IP
echo -e "${BLUE}🌐 Getting public IP...${NC}"
TASK_INFO=$(aws ecs describe-tasks --cluster $ECS_CLUSTER --tasks $TASK_ARN --region $AWS_REGION)
PUBLIC_IP=$(echo $TASK_INFO | jq -r '.tasks[0].attachments[0].details[] | select(.name=="networkInterfaceId") | .value' | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region $AWS_REGION)

# 8. Health Check
echo -e "${BLUE}🔍 Running health check...${NC}"
sleep 30  # Wait for service to start

if curl -f http://$PUBLIC_IP:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo -e "${BLUE}🌐 API Server URL: http://$PUBLIC_IP:5001${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed - service may still be starting${NC}"
fi

# 9. Create Lambda Function for Historical Data
echo -e "${BLUE}📊 Creating Lambda function for historical data collection...${NC}"

# Create Lambda deployment package
cd lambda
zip -r historical-collection-lambda.zip historical-collection.py
cd ..

# Create Lambda function
if aws lambda get-function --function-name crypto-historical-collection --region $AWS_REGION > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Lambda function already exists${NC}"
else
    aws lambda create-function \
        --function-name crypto-historical-collection \
        --runtime python3.12 \
        --role arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-execution-role \
        --handler historical-collection.lambda_handler \
        --zip-file fileb://lambda/historical-collection-lambda.zip \
        --timeout 900 \
        --memory-size 1024 \
        --region $AWS_REGION
    echo -e "${GREEN}✅ Lambda function created${NC}"
fi

# 10. Create API Gateway for Lambda
echo -e "${BLUE}🌐 Creating API Gateway...${NC}"

# Create API Gateway
API_ID=$(aws apigateway create-rest-api --name crypto-historical-api --query 'id' --output text --region $AWS_REGION)
echo -e "${GREEN}✅ API Gateway created: $API_ID${NC}"

# Get root resource
ROOT_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query 'items[0].id' --output text --region $AWS_REGION)

# Create resource
RESOURCE_ID=$(aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_RESOURCE_ID --path-part historical --query 'id' --output text --region $AWS_REGION)

# Create method
aws apigateway put-method --rest-api-id $API_ID --resource-id $RESOURCE_ID --http-method POST --authorization-type NONE --region $AWS_REGION

# Set up Lambda integration
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:crypto-historical-collection/invocations \
    --region $AWS_REGION

# Deploy API
aws apigateway create-deployment --rest-api-id $API_ID --stage-name prod --region $AWS_REGION

echo ""
echo -e "${GREEN}🎉 AWS Deployment Complete!${NC}"
echo "=================================="
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo -e "  ECR Repository: $ECR_REPOSITORY"
echo -e "  ECS Cluster: $ECS_CLUSTER"
echo -e "  ECS Service: $ECS_SERVICE"
echo -e "  API Server URL: http://$PUBLIC_IP:5001"
echo -e "  Lambda Function: crypto-historical-collection"
echo -e "  API Gateway: $API_ID"
echo ""
echo -e "${BLUE}🚀 Available Endpoints:${NC}"
echo -e "  Health Check: http://$PUBLIC_IP:5001/health"
echo -e "  Real-time Data: http://$PUBLIC_IP:5001/realtime"
echo -e "  Historical Data: http://$PUBLIC_IP:5001/historical"
echo -e "  Exchanges: http://$PUBLIC_IP:5001/exchanges"
echo -e "  Symbols: http://$PUBLIC_IP:5001/symbols"
echo ""
echo -e "${BLUE}📝 Useful Commands:${NC}"
echo -e "  Check service status:"
echo -e "    aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE"
echo -e "  View logs:"
echo -e "    aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id"
echo -e "  Trigger historical collection:"
echo -e "    curl -X POST https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/prod/historical"
echo ""
echo -e "${BLUE}🔧 Next Steps:${NC}"
echo -e "  1. Set up GitHub repository"
echo -e "  2. Add GitHub secrets for CI/CD"
echo -e "  3. Push code to trigger automatic deployment"
echo -e "  4. Monitor service health and logs"
