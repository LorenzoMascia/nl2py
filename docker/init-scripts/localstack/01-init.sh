#!/bin/bash

# LocalStack Initialization Script for NL2Py
# This script sets up AWS resources for local development and testing
# Run automatically when LocalStack starts

echo "Initializing LocalStack AWS resources for NL2Py..."

# Set AWS credentials for awslocal
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# ============================================
# S3 Buckets
# ============================================
echo "Creating S3 buckets..."

awslocal s3 mb s3://nl2py-bucket 2>/dev/null || true
awslocal s3 mb s3://nl2py-uploads 2>/dev/null || true
awslocal s3 mb s3://nl2py-data 2>/dev/null || true
awslocal s3 mb s3://nl2py-logs 2>/dev/null || true

# Upload sample files
echo '{"message": "Hello from S3"}' | awslocal s3 cp - s3://nl2py-bucket/test.json
echo "Sample CSV data" | awslocal s3 cp - s3://nl2py-data/sample.csv

echo "S3 buckets created"

# ============================================
# DynamoDB Tables
# ============================================
echo "Creating DynamoDB tables..."

# Users table
awslocal dynamodb create-table \
    --table-name users \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    2>/dev/null || true

# Orders table
awslocal dynamodb create-table \
    --table-name orders \
    --attribute-definitions \
        AttributeName=order_id,AttributeType=S \
        AttributeName=customer_id,AttributeType=S \
    --key-schema \
        AttributeName=order_id,KeyType=HASH \
    --global-secondary-indexes \
        "[{\"IndexName\":\"CustomerIdIndex\",\"KeySchema\":[{\"AttributeName\":\"customer_id\",\"KeyType\":\"HASH\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}]" \
    --billing-mode PAY_PER_REQUEST \
    2>/dev/null || true

# Events table (with timestamp)
awslocal dynamodb create-table \
    --table-name events \
    --attribute-definitions \
        AttributeName=event_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=N \
    --key-schema \
        AttributeName=event_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    2>/dev/null || true

# Insert sample data
awslocal dynamodb put-item \
    --table-name users \
    --item '{"user_id":{"S":"user-001"},"name":{"S":"Alice"},"email":{"S":"alice@example.com"},"age":{"N":"30"}}' \
    2>/dev/null || true

awslocal dynamodb put-item \
    --table-name users \
    --item '{"user_id":{"S":"user-002"},"name":{"S":"Bob"},"email":{"S":"bob@example.com"},"age":{"N":"25"}}' \
    2>/dev/null || true

echo "DynamoDB tables created"

# ============================================
# SQS Queues
# ============================================
echo "Creating SQS queues..."

awslocal sqs create-queue --queue-name nl2py-queue 2>/dev/null || true
awslocal sqs create-queue --queue-name orders-queue 2>/dev/null || true
awslocal sqs create-queue --queue-name events-queue 2>/dev/null || true
awslocal sqs create-queue --queue-name tasks-queue 2>/dev/null || true

# Create dead-letter queue
awslocal sqs create-queue --queue-name nl2py-dlq 2>/dev/null || true

# Send sample messages
awslocal sqs send-message \
    --queue-url http://localhost:4566/000000000000/nl2py-queue \
    --message-body '{"message":"Test message from LocalStack"}' \
    2>/dev/null || true

echo "SQS queues created"

# ============================================
# SNS Topics
# ============================================
echo "Creating SNS topics..."

awslocal sns create-topic --name nl2py-notifications 2>/dev/null || true
awslocal sns create-topic --name nl2py-alerts 2>/dev/null || true
awslocal sns create-topic --name nl2py-events 2>/dev/null || true

# Subscribe queue to topic (SNS -> SQS)
TOPIC_ARN=$(awslocal sns list-topics --query 'Topics[?contains(TopicArn, `nl2py-notifications`)].TopicArn' --output text)
QUEUE_ARN=$(awslocal sqs get-queue-attributes --queue-url http://localhost:4566/000000000000/events-queue --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

awslocal sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol sqs \
    --notification-endpoint $QUEUE_ARN \
    2>/dev/null || true

echo "SNS topics created"

# ============================================
# Lambda Functions
# ============================================
echo "Creating Lambda functions..."

# Create sample Lambda function (Node.js)
mkdir -p /tmp/lambda
cat > /tmp/lambda/index.js << 'EOF'
exports.handler = async (event) => {
    console.log('Event:', JSON.stringify(event));
    return {
        statusCode: 200,
        body: JSON.stringify({
            message: 'Hello from LocalStack Lambda!',
            input: event
        })
    };
};
EOF

cd /tmp/lambda
zip -q function.zip index.js

awslocal lambda create-function \
    --function-name nl2py-test-function \
    --runtime nodejs20.x \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --handler index.handler \
    --zip-file fileb://function.zip \
    2>/dev/null || true

cd /
rm -rf /tmp/lambda

echo "Lambda functions created"

# ============================================
# Secrets Manager
# ============================================
echo "Creating secrets..."

awslocal secretsmanager create-secret \
    --name database/dev/credentials \
    --secret-string '{"username":"admin","password":"devpassword123"}' \
    2>/dev/null || true

awslocal secretsmanager create-secret \
    --name api/dev/key \
    --secret-string '{"api_key":"dev-api-key-12345","api_secret":"dev-secret-67890"}' \
    2>/dev/null || true

echo "Secrets created"

# ============================================
# CloudWatch Log Groups
# ============================================
echo "Creating CloudWatch log groups..."

awslocal logs create-log-group --log-group-name /nl2py/application 2>/dev/null || true
awslocal logs create-log-group --log-group-name /nl2py/errors 2>/dev/null || true
awslocal logs create-log-group --log-group-name /aws/lambda/nl2py-test-function 2>/dev/null || true

echo "CloudWatch log groups created"

# ============================================
# EventBridge Rules
# ============================================
echo "Creating EventBridge rules..."

awslocal events put-rule \
    --name nl2py-scheduled-task \
    --schedule-expression "rate(5 minutes)" \
    2>/dev/null || true

echo "EventBridge rules created"

# ============================================
# Summary
# ============================================
echo ""
echo "========================================"
echo "LocalStack initialization complete!"
echo "========================================"
echo ""
echo "Created resources:"
echo "  - S3 Buckets: nl2py-bucket, nl2py-uploads, nl2py-data, nl2py-logs"
echo "  - DynamoDB Tables: users, orders, events"
echo "  - SQS Queues: nl2py-queue, orders-queue, events-queue, tasks-queue, nl2py-dlq"
echo "  - SNS Topics: nl2py-notifications, nl2py-alerts, nl2py-events"
echo "  - Lambda Functions: nl2py-test-function"
echo "  - Secrets: database/dev/credentials, api/dev/key"
echo "  - CloudWatch Log Groups: /nl2py/application, /nl2py/errors"
echo ""
echo "Access LocalStack at: http://localhost:4566"
echo "AWS CLI: aws --endpoint-url=http://localhost:4566 <command>"
echo "========================================"
