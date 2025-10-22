#!/bin/bash

# Get Current API Public IP
# This script gets the current public IP of the running ECS service

set -e

AWS_REGION="us-east-1"
ECS_CLUSTER="crypto-data-cluster"
ECS_SERVICE="crypto-api-service"

echo "🔍 Getting current API public IP..."

# Get the task ARN
TASK_ARN=$(aws ecs list-tasks --cluster $ECS_CLUSTER --service-name $ECS_SERVICE --region $AWS_REGION --query 'taskArns[0]' --output text)

if [ "$TASK_ARN" = "None" ] || [ -z "$TASK_ARN" ]; then
    echo "❌ No running tasks found for service $ECS_SERVICE"
    exit 1
fi

echo "📋 Task ARN: $TASK_ARN"

# Get the network interface ID
ENI_ID=$(aws ecs describe-tasks --cluster $ECS_CLUSTER --tasks $TASK_ARN --region $AWS_REGION --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)

if [ "$ENI_ID" = "None" ] || [ -z "$ENI_ID" ]; then
    echo "❌ No network interface found for task"
    exit 1
fi

echo "🌐 ENI ID: $ENI_ID"

# Get the public IP
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region $AWS_REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

if [ "$PUBLIC_IP" = "None" ] || [ -z "$PUBLIC_IP" ]; then
    echo "❌ No public IP found for network interface"
    exit 1
fi

echo ""
echo "🎉 Current API Public IP: $PUBLIC_IP"
echo ""
echo "📊 Available Endpoints:"
echo "  Health Check: http://$PUBLIC_IP:5001/health"
echo "  Latest Data:  http://$PUBLIC_IP:5001/latest"
echo "  Kraken Data:  http://$PUBLIC_IP:5001/latest/kraken"
echo "  API Info:     http://$PUBLIC_IP:5001/"
echo ""
echo "🧪 Test Commands:"
echo "  curl http://$PUBLIC_IP:5001/health"
echo "  curl http://$PUBLIC_IP:5001/latest | jq '.data | keys'"
echo "  curl http://$PUBLIC_IP:5001/latest/kraken | jq '.data.market_data'"
