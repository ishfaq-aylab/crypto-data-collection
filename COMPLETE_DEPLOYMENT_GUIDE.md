# 🚀 Complete Deployment Guide: From Local to AWS

Step-by-step guide to deploy your crypto data collection system from local development to AWS production.

## 📋 Prerequisites Checklist

- [ ] AWS Account with console access
- [ ] AWS CLI installed and configured
- [ ] Docker installed
- [ ] GitHub account
- [ ] Your code is ready locally

## 🎯 Step 1: Initialize Git Repository

### 1.1 Initialize Git (if not already done)
```bash
# Check if git is already initialized
ls -la | grep .git

# If not initialized, run:
git init
```

### 1.2 Add All Files to Git
```bash
# Add all files to git
git add .

# Check what files are staged
git status

# Commit the initial version
git commit -m "Initial commit: Crypto data collection system with AWS deployment"
```

### 1.3 Create .gitignore (if not exists)
```bash
# Create .gitignore file
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Environment variables
.env
.env.local
.env.production

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# AWS
.aws/

# Docker
.dockerignore

# PID files
*.pid

# Temporary files
tmp/
temp/
EOF

# Add .gitignore to git
git add .gitignore
git commit -m "Add .gitignore file"
```

## 🐙 Step 2: Create GitHub Repository

### 2.1 Create Repository on GitHub
1. Go to [GitHub.com](https://github.com)
2. Click "New repository" (green button)
3. Repository name: `crypto-data-collection`
4. Description: `Real-time crypto data collection system with AWS deployment`
5. Make it **Public** (for easier setup)
6. **Don't** initialize with README, .gitignore, or license (we have files already)
7. Click "Create repository"

### 2.2 Connect Local Repository to GitHub
```bash
# Add remote origin (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/crypto-data-collection.git

# Verify remote is added
git remote -v

# Push to GitHub
git push -u origin main
```

If you get an error about authentication, you'll need to set up GitHub authentication:

```bash
# Option 1: Use GitHub CLI (recommended)
gh auth login

# Option 2: Use personal access token
# Go to GitHub Settings > Developer settings > Personal access tokens
# Create a new token with repo permissions
# Then use:
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/crypto-data-collection.git
```

## 🔧 Step 3: Configure AWS CLI

### 3.1 Install AWS CLI (if not installed)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install awscli

# macOS
brew install awscli

# Windows
# Download from: https://aws.amazon.com/cli/
```

### 3.2 Configure AWS CLI
```bash
# Configure AWS CLI
aws configure

# You'll be prompted for:
# AWS Access Key ID: [Enter your access key]
# AWS Secret Access Key: [Enter your secret key]
# Default region name: us-east-1
# Default output format: json
```

### 3.3 Verify AWS Configuration
```bash
# Test AWS connection
aws sts get-caller-identity

# Should return your AWS account information
```

## 🏗️ Step 4: Deploy to AWS

### 4.1 Run Quick Deployment
```bash
# Make sure you're in the project directory
cd /home/ishfaq/Documents/dev/aylabs/exchanges-websockets

# Run the quick deployment script
./quick-deploy.sh
```

This script will:
- Create all AWS infrastructure
- Build and push Docker image
- Deploy ECS service
- Run health checks

### 4.2 Monitor Deployment
```bash
# Watch the deployment progress
# The script will show you the progress and any errors

# If you need to check manually:
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service
```

### 4.3 Get Service URL
After deployment, you'll see output like:
```
🌐 API Server URL: http://YOUR_PUBLIC_IP:5001
```

## 🔄 Step 5: Set Up CI/CD Pipeline

### 5.1 Add GitHub Secrets
1. Go to your GitHub repository
2. Click "Settings" tab
3. Click "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Add these secrets one by one:

```
Name: AWS_ACCESS_KEY_ID
Value: [Your AWS Access Key ID]

Name: AWS_SECRET_ACCESS_KEY
Value: [Your AWS Secret Access Key]

Name: MONGODB_URL
Value: mongodb://localhost:27017

Name: MONGODB_DATABASE
Value: model-collections
```

### 5.2 Test CI/CD Pipeline
```bash
# Make a small change to test the pipeline
echo "# Test CI/CD Pipeline" >> README.md

# Add and commit the change
git add README.md
git commit -m "Test CI/CD pipeline"

# Push to GitHub
git push origin main

# Check GitHub Actions tab for deployment status
# Go to: https://github.com/YOUR_USERNAME/crypto-data-collection/actions
```

## 📊 Step 6: Verify Deployment

### 6.1 Test API Endpoints
```bash
# Replace YOUR_PUBLIC_IP with the actual IP from deployment
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

### 6.2 Check Service Status
```bash
# Check ECS service status
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# Check service logs
aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id
```

### 6.3 Monitor Data Collection
```bash
# Check if data is being collected
curl $API_URL/health/detailed

# This should show recent data counts for each exchange
```

## 🔧 Step 7: Production Optimization

### 7.1 Set Up Monitoring
```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard --dashboard-name "Crypto-Data-Dashboard" --dashboard-body '{
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
}'
```

### 7.2 Configure Auto-scaling
```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/crypto-data-cluster/crypto-api-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/crypto-data-cluster/crypto-api-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name crypto-api-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    }
  }'
```

## 📈 Step 8: Historical Data Collection

### 8.1 Create Lambda Function
```bash
# Create Lambda deployment package
cd lambda
zip -r historical-collection-lambda.zip historical-collection.py
cd ..

# Create Lambda function
aws lambda create-function \
  --function-name crypto-historical-collection \
  --runtime python3.12 \
  --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
  --handler historical-collection.lambda_handler \
  --zip-file fileb://lambda/historical-collection-lambda.zip \
  --timeout 900 \
  --memory-size 1024
```

### 8.2 Test Historical Data Collection
```bash
# Test Lambda function
aws lambda invoke \
  --function-name crypto-historical-collection \
  --payload '{"start_date": "2024-01-01", "end_date": "2024-01-31", "exchanges": ["binance"], "symbols": ["BTCUSDT"], "timeframes": ["1h"]}' \
  response.json

# Check response
cat response.json
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Git Push Fails
```bash
# If you get authentication error:
gh auth login

# Or use personal access token:
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/crypto-data-collection.git
```

#### 2. AWS CLI Not Configured
```bash
# Configure AWS CLI
aws configure

# Test connection
aws sts get-caller-identity
```

#### 3. Docker Build Fails
```bash
# Check Docker is running
docker --version

# Start Docker if needed
sudo systemctl start docker
sudo systemctl enable docker
```

#### 4. ECS Service Not Starting
```bash
# Check service status
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# Check task logs
aws logs get-log-events --log-group-name /ecs/crypto-api --log-stream-name ecs/crypto-api/container-id
```

#### 5. API Not Responding
```bash
# Check if service is running
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# Test health endpoint
curl http://YOUR_PUBLIC_IP:5001/health

# Check logs
aws logs tail /ecs/crypto-api --follow
```

## 📊 Step 9: Verify Everything Works

### 9.1 Complete System Test
```bash
# 1. Test API health
curl http://YOUR_PUBLIC_IP:5001/health

# 2. Test real-time data
curl http://YOUR_PUBLIC_IP:5001/realtime

# 3. Test historical data
curl http://YOUR_PUBLIC_IP:5001/historical

# 4. Test exchanges
curl http://YOUR_PUBLIC_IP:5001/exchanges

# 5. Test symbols
curl http://YOUR_PUBLIC_IP:5001/symbols
```

### 9.2 Check Data Collection
```bash
# Check if data is being collected
curl http://YOUR_PUBLIC_IP:5001/health/detailed

# This should show recent data counts for each exchange
```

### 9.3 Monitor Logs
```bash
# Monitor application logs
aws logs tail /ecs/crypto-api --follow

# Monitor data collection logs
aws logs tail /ecs/crypto-data-collection --follow
```

## 🎉 Success Checklist

- [ ] Git repository initialized and pushed to GitHub
- [ ] AWS CLI configured and working
- [ ] AWS infrastructure created
- [ ] Docker image built and pushed
- [ ] ECS service running
- [ ] API endpoints responding
- [ ] Real-time data collection working
- [ ] Historical data collection available
- [ ] CI/CD pipeline working
- [ ] Monitoring configured
- [ ] Health checks passing

## 🚀 Next Steps

### Immediate Actions
1. **Test**: Verify all endpoints work
2. **Monitor**: Check health and logs
3. **Scale**: Configure auto-scaling
4. **Backup**: Set up database backups

### Future Enhancements
1. **Custom Domain**: Set up Route 53
2. **SSL Certificate**: Enable HTTPS
3. **Advanced Monitoring**: Set up alerts
4. **Cost Optimization**: Review and optimize costs

---

## 📞 Quick Commands Reference

```bash
# Git operations
git add .
git commit -m "Your message"
git push origin main

# AWS operations
aws sts get-caller-identity
aws ecs describe-services --cluster crypto-data-cluster --services crypto-api-service

# Test API
curl http://YOUR_PUBLIC_IP:5001/health
curl http://YOUR_PUBLIC_IP:5001/realtime

# Monitor logs
aws logs tail /ecs/crypto-api --follow
```

Your deployment is now complete! 🎉
