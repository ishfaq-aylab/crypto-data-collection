# 🚀 AWS Deployment Guide

Complete guide for deploying the Crypto Data Collection System on AWS with CI/CD, auto-deployment, and parallel services.

## 📋 Prerequisites

- AWS Account with console access
- GitHub repository
- AWS CLI configured
- Docker installed locally
- Domain name (optional, for custom domain)

## 🏗️ AWS Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub Repo   │    │   AWS ECS       │    │   AWS RDS       │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Code      │ │───▶│ │ API Server  │ │    │ │ MongoDB     │ │
│ │             │ │    │ │             │ │    │ │             │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │                 │
│ │   Actions   │ │───▶│ │ Data        │ │    │                 │
│ │             │ │    │ │ Collection  │ │    │                 │
│ └─────────────┘ │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Step 1: AWS Infrastructure Setup

### 1.1 Create AWS Resources

```bash
# Create infrastructure using AWS CDK or CloudFormation
aws cloudformation create-stack \
  --stack-name crypto-data-infrastructure \
  --template-body file://infrastructure.yaml \
  --capabilities CAPABILITY_IAM
```

### 1.2 Required AWS Services

- **ECS (Elastic Container Service)** - Container orchestration
- **ECR (Elastic Container Registry)** - Docker image storage
- **RDS (Relational Database Service)** - MongoDB Atlas or DocumentDB
- **Application Load Balancer** - Traffic distribution
- **CloudWatch** - Monitoring and logging
- **IAM** - Security and permissions
- **VPC** - Network isolation
- **Route 53** - DNS management (optional)

## 🐳 Step 2: Docker Configuration

### 2.1 Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements_production.txt .
RUN pip install --no-cache-dir -r requirements_production.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Default command
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:application"]
```

### 2.2 Create docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  api-server:
    build: .
    ports:
      - "5001:5001"
    environment:
      - MONGODB_URL=${MONGODB_URL}
      - MONGODB_DATABASE=${MONGODB_DATABASE}
      - API_HOST=0.0.0.0
      - API_PORT=5001
    depends_on:
      - mongodb
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  data-collection:
    build: .
    command: python run_data_collection.py
    environment:
      - MONGODB_URL=${MONGODB_URL}
      - MONGODB_DATABASE=${MONGODB_DATABASE}
    depends_on:
      - mongodb
    restart: unless-stopped

  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    restart: unless-stopped

volumes:
  mongodb_data:
```

## 🔄 Step 3: GitHub Actions CI/CD

### 3.1 Create GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: crypto-data-api
  ECS_SERVICE: crypto-api-service
  ECS_CLUSTER: crypto-data-cluster
  ECS_TASK_DEFINITION: crypto-api-task

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements_production.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          python -m pytest tests/ --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build, tag, and push image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
      
      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition $ECS_TASK_DEFINITION \
            --query taskDefinition > task-definition.json
      
      - name: Fill in the new image ID
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: crypto-api
          image: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
      
      - name: Deploy Amazon ECS task definition
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

### 3.2 Create ECS Task Definition

```json
{
  "family": "crypto-api-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "api-server",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest",
      "portMappings": [
        {
          "containerPort": 5001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MONGODB_URL",
          "value": "mongodb://mongodb:27017"
        },
        {
          "name": "MONGODB_DATABASE",
          "value": "crypto_trading_data"
        },
        {
          "name": "API_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "API_PORT",
          "value": "5001"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/crypto-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:5001/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    },
    {
      "name": "data-collection",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest",
      "command": ["python", "run_data_collection.py"],
      "environment": [
        {
          "name": "MONGODB_URL",
          "value": "mongodb://mongodb:27017"
        },
        {
          "name": "MONGODB_DATABASE",
          "value": "crypto_trading_data"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/crypto-data-collection",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## 🔧 Step 4: AWS Infrastructure Setup

### 4.1 Create VPC and Networking

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=crypto-data-vpc}]'

# Create subnets
aws ec2 create-subnet --vpc-id vpc-xxxxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxxxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create internet gateway
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=crypto-data-igw}]'
```

### 4.2 Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name crypto-data-cluster

# Create ECR repository
aws ecr create-repository --repository-name crypto-data-api
```

### 4.3 Create IAM Roles

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## 📊 Step 5: Monitoring and Logging

### 5.1 CloudWatch Configuration

```bash
# Create CloudWatch log groups
aws logs create-log-group --log-group-name /ecs/crypto-api
aws logs create-log-group --log-group-name /ecs/crypto-data-collection

# Create CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "crypto-api-high-cpu" \
  --alarm-description "High CPU usage for crypto API" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 5.2 Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name crypto-data-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx \
  --scheme internet-facing \
  --type application
```

## 🚀 Step 6: Deployment Commands

### 6.1 Initial Setup

```bash
# 1. Configure AWS CLI
aws configure

# 2. Create ECR repository
aws ecr create-repository --repository-name crypto-data-api

# 3. Build and push Docker image
docker build -t crypto-data-api .
docker tag crypto-data-api:latest ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/crypto-data-api:latest

# 4. Create ECS cluster
aws ecs create-cluster --cluster-name crypto-data-cluster

# 5. Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 6. Create ECS service
aws ecs create-service \
  --cluster crypto-data-cluster \
  --service-name crypto-api-service \
  --task-definition crypto-api-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}"
```

### 6.2 GitHub Secrets Setup

Add these secrets to your GitHub repository:

```
AWS_ACCESS_KEY_ID: your-access-key
AWS_SECRET_ACCESS_KEY: your-secret-key
MONGODB_URL: your-mongodb-connection-string
MONGODB_DATABASE: crypto_trading_data
```

## 📈 Step 7: Historical Data Collection

### 7.1 On-Demand Historical Collection

```bash
# Create Lambda function for historical data collection
aws lambda create-function \
  --function-name crypto-historical-collection \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://historical-collection.zip
```

### 7.2 Lambda Function for Historical Data

```python
# lambda_function.py
import json
import boto3
import subprocess
import os

def lambda_handler(event, context):
    """
    Lambda function to trigger historical data collection
    """
    try:
        # Parse event parameters
        start_date = event.get('start_date', '2021-01-01')
        end_date = event.get('end_date', '2024-12-31')
        exchanges = event.get('exchanges', ['binance', 'bybit', 'kraken', 'gate'])
        
        # Set environment variables
        os.environ['MONGODB_URL'] = event.get('mongodb_url', 'mongodb://localhost:27017')
        os.environ['MONGODB_DATABASE'] = event.get('mongodb_database', 'crypto_trading_data')
        
        # Run historical collection
        result = subprocess.run([
            'python', 'manage_historical_collection.py', 'start',
            '--start-date', start_date,
            '--end-date', end_date,
            '--exchanges', ','.join(exchanges)
        ], capture_output=True, text=True)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Historical data collection started',
                'output': result.stdout,
                'error': result.stderr
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
```

## 🔄 Step 8: Auto-Deployment Setup

### 8.1 GitHub Actions Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add the following secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `MONGODB_URL`
   - `MONGODB_DATABASE`

### 8.2 Branch Protection Rules

1. Go to repository Settings → Branches
2. Add rule for `main` branch
3. Enable "Require pull request reviews before merging"
4. Enable "Require status checks to pass before merging"
5. Select the "test" job as required

## 📊 Step 9: Monitoring Dashboard

### 9.1 CloudWatch Dashboard

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ECS", "CPUUtilization", "ServiceName", "crypto-api-service"],
          ["AWS/ECS", "MemoryUtilization", "ServiceName", "crypto-api-service"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ECS Service Metrics"
      }
    }
  ]
}
```

### 9.2 Health Check Endpoint

```python
# Add to your API server
@app.route('/health/detailed')
def detailed_health():
    """Detailed health check for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'api_server': 'running',
            'data_collection': 'running',
            'database': 'connected'
        },
        'metrics': {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
    })
```

## 🎯 Step 10: Production Checklist

### 10.1 Pre-Deployment

- [ ] AWS CLI configured
- [ ] GitHub repository created
- [ ] GitHub secrets added
- [ ] Docker image builds successfully
- [ ] ECR repository created
- [ ] ECS cluster created
- [ ] Task definition registered
- [ ] Load balancer configured
- [ ] Security groups configured
- [ ] CloudWatch log groups created

### 10.2 Post-Deployment

- [ ] API server responding
- [ ] Data collection running
- [ ] Database connected
- [ ] Health checks passing
- [ ] Monitoring active
- [ ] Logs flowing
- [ ] Auto-scaling configured
- [ ] Backup strategy implemented

## 🚨 Troubleshooting

### Common Issues

1. **ECS Service Not Starting**
   ```bash
   # Check service status
   aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service
   
   # Check task logs
   aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id
   ```

2. **Database Connection Issues**
   ```bash
   # Check security groups
   aws ec2 describe-security-groups --group-ids sg-xxxxx
   
   # Test connectivity
   aws ecs run-task --cluster crypto-data-cluster --task-definition crypto-api-task
   ```

3. **GitHub Actions Failing**
   ```bash
   # Check AWS credentials
   aws sts get-caller-identity
   
   # Verify ECR permissions
   aws ecr describe-repositories --repository-names crypto-data-api
   ```

## 📞 Support

For issues and questions:
- Check CloudWatch logs
- Monitor ECS service status
- Review GitHub Actions logs
- Check AWS support documentation

---

## 🎉 Quick Start Commands

```bash
# 1. Setup AWS CLI
aws configure

# 2. Create infrastructure
./scripts/setup-aws-infrastructure.sh

# 3. Deploy application
git push origin main

# 4. Monitor deployment
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# 5. Check health
curl https://your-alb-url/health
```
