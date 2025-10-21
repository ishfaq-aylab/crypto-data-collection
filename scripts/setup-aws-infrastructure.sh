#!/bin/bash
# AWS Infrastructure Setup Script
# ================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up AWS Infrastructure for Crypto Data Collection${NC}"
echo "=============================================================="

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="crypto-data-api"
ECS_CLUSTER="crypto-data-cluster"
ECS_SERVICE="crypto-api-service"
ECS_TASK_DEFINITION="crypto-api-task"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI configured${NC}"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${BLUE}📊 AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# 1. Create ECR Repository
echo -e "${BLUE}📦 Creating ECR repository...${NC}"
if aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  ECR repository already exists${NC}"
else
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
    echo -e "${GREEN}✅ ECR repository created${NC}"
fi

# 2. Create ECS Cluster
echo -e "${BLUE}🏗️  Creating ECS cluster...${NC}"
if aws ecs describe-clusters --clusters $ECS_CLUSTER --region $AWS_REGION > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  ECS cluster already exists${NC}"
else
    aws ecs create-cluster --cluster-name $ECS_CLUSTER --region $AWS_REGION
    echo -e "${GREEN}✅ ECS cluster created${NC}"
fi

# 3. Create CloudWatch Log Groups
echo -e "${BLUE}📝 Creating CloudWatch log groups...${NC}"
for log_group in "/ecs/crypto-api" "/ecs/crypto-data-collection"; do
    if aws logs describe-log-groups --log-group-name-prefix $log_group --region $AWS_REGION > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Log group $log_group already exists${NC}"
    else
        aws logs create-log-group --log-group-name $log_group --region $AWS_REGION
        echo -e "${GREEN}✅ Log group $log_group created${NC}"
    fi
done

# 4. Create VPC (if not exists)
echo -e "${BLUE}🌐 Setting up VPC...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=crypto-data-vpc" --query 'Vpcs[0].VpcId' --output text --region $AWS_REGION)
if [ "$VPC_ID" = "None" ] || [ "$VPC_ID" = "" ]; then
    echo -e "${BLUE}📡 Creating VPC...${NC}"
    VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=crypto-data-vpc}]' --query 'Vpc.VpcId' --output text --region $AWS_REGION)
    echo -e "${GREEN}✅ VPC created: $VPC_ID${NC}"
else
    echo -e "${YELLOW}⚠️  VPC already exists: $VPC_ID${NC}"
fi

# 5. Create Subnets
echo -e "${BLUE}📡 Creating subnets...${NC}"
SUBNET_1=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=availability-zone,Values=us-east-1a" --query 'Subnets[0].SubnetId' --output text --region $AWS_REGION)
if [ "$SUBNET_1" = "None" ] || [ "$SUBNET_1" = "" ]; then
    SUBNET_1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=crypto-data-subnet-1}]' --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
    echo -e "${GREEN}✅ Subnet 1 created: $SUBNET_1${NC}"
else
    echo -e "${YELLOW}⚠️  Subnet 1 already exists: $SUBNET_1${NC}"
fi

SUBNET_2=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=availability-zone,Values=us-east-1b" --query 'Subnets[0].SubnetId' --output text --region $AWS_REGION)
if [ "$SUBNET_2" = "None" ] || [ "$SUBNET_2" = "" ]; then
    SUBNET_2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=crypto-data-subnet-2}]' --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
    echo -e "${GREEN}✅ Subnet 2 created: $SUBNET_2${NC}"
else
    echo -e "${YELLOW}⚠️  Subnet 2 already exists: $SUBNET_2${NC}"
fi

# 6. Create Internet Gateway
echo -e "${BLUE}🌐 Creating Internet Gateway...${NC}"
IGW_ID=$(aws ec2 describe-internet-gateways --filters "Name=tag:Name,Values=crypto-data-igw" --query 'InternetGateways[0].InternetGatewayId' --output text --region $AWS_REGION)
if [ "$IGW_ID" = "None" ] || [ "$IGW_ID" = "" ]; then
    IGW_ID=$(aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=crypto-data-igw}]' --query 'InternetGateway.InternetGatewayId' --output text --region $AWS_REGION)
    aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID --region $AWS_REGION
    echo -e "${GREEN}✅ Internet Gateway created: $IGW_ID${NC}"
else
    echo -e "${YELLOW}⚠️  Internet Gateway already exists: $IGW_ID${NC}"
fi

# 7. Create Security Group
echo -e "${BLUE}🔒 Creating Security Group...${NC}"
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=crypto-data-sg" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION)
if [ "$SG_ID" = "None" ] || [ "$SG_ID" = "" ]; then
    SG_ID=$(aws ec2 create-security-group --group-name crypto-data-sg --description "Security group for crypto data collection" --vpc-id $VPC_ID --query 'GroupId' --output text --region $AWS_REGION)
    
    # Allow HTTP traffic
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $AWS_REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $AWS_REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5001 --cidr 0.0.0.0/0 --region $AWS_REGION
    
    echo -e "${GREEN}✅ Security Group created: $SG_ID${NC}"
else
    echo -e "${YELLOW}⚠️  Security Group already exists: $SG_ID${NC}"
fi

# 8. Update task definition with actual values
echo -e "${BLUE}📝 Updating task definition...${NC}"
sed -i "s/ACCOUNT/$AWS_ACCOUNT_ID/g" ecs-task-definition.json
sed -i "s/us-east-1/$AWS_REGION/g" ecs-task-definition.json

# 9. Register Task Definition
echo -e "${BLUE}📋 Registering task definition...${NC}"
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json --region $AWS_REGION
echo -e "${GREEN}✅ Task definition registered${NC}"

# 10. Create ECS Service
echo -e "${BLUE}🚀 Creating ECS service...${NC}"
if aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  ECS service already exists${NC}"
else
    aws ecs create-service \
        --cluster $ECS_CLUSTER \
        --service-name $ECS_SERVICE \
        --task-definition $ECS_TASK_DEFINITION \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
        --region $AWS_REGION
    echo -e "${GREEN}✅ ECS service created${NC}"
fi

echo ""
echo -e "${GREEN}🎉 AWS Infrastructure Setup Complete!${NC}"
echo "=============================================="
echo -e "${BLUE}📊 Summary:${NC}"
echo -e "  ECR Repository: $ECR_REPOSITORY"
echo -e "  ECS Cluster: $ECS_CLUSTER"
echo -e "  ECS Service: $ECS_SERVICE"
echo -e "  VPC ID: $VPC_ID"
echo -e "  Subnet 1: $SUBNET_1"
echo -e "  Subnet 2: $SUBNET_2"
echo -e "  Security Group: $SG_ID"
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo -e "  1. Push your code to GitHub"
echo -e "  2. Add GitHub secrets:"
echo -e "     - AWS_ACCESS_KEY_ID"
echo -e "     - AWS_SECRET_ACCESS_KEY"
echo -e "     - MONGODB_URL"
echo -e "     - MONGODB_DATABASE"
echo -e "  3. The CI/CD pipeline will automatically deploy"
echo ""
echo -e "${BLUE}📝 Useful Commands:${NC}"
echo -e "  Check service status:"
echo -e "    aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE"
echo -e "  View logs:"
echo -e "    aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id"
echo -e "  Update service:"
echo -e "    aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --force-new-deployment"
