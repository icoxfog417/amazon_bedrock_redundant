# Amazon Bedrock Redundant API

This project implements a redundant API for Amazon Bedrock, allowing fallback to different models and regions.

## Features

- Redundant model invocation across multiple AWS regions
- AWS X-Ray tracing integration
- REST API using Amazon API Gateway
- Serverless architecture using AWS Lambda

## Prerequisites

- AWS SAM CLI installed
- Python 3.11 or later
- AWS credentials configured locally

## Project Structure

```
.
├── config/
│   └── models.yaml          # Model configuration
├── src/
│   ├── lambda_function.py   # Lambda function code
│   └── requirements.txt     # Python dependencies (auto-installed by SAM)
├── tests/
│   └── test_lambda_function.py
└── template.yaml           # SAM template
```

## Setup and Deployment

1. Install AWS SAM CLI:
   ```bash
   uv add aws-sam-cli
   ```

2. Configure your AWS credentials:
   ```bash
   aws configure
   ```

3. Build the application:
   ```bash
   sam build
   ```

4. Deploy the application:
   ```bash
   sam deploy --guided
   ```

   During the guided deployment, you will be prompted to:
   - Enter a unique stack name
   - Choose an AWS Region
   - Confirm creation of IAM roles
   
   The deployment will automatically:
   - Install Python dependencies from src/requirements.txt
   - Set up the API Gateway endpoint
   - Configure Lambda function with proper permissions
   - Set up X-Ray tracing
   - Load model configuration from config/models.yaml

## Development

To run the tests locally:
```bash
python -m pytest tests/
```

To invoke the function locally:
```bash
sam local invoke BedrockRedundantFunction -e events/event.json
```

## API Usage

Send a POST request to the deployed API endpoint with the following body structure:

```bash
curl -X POST \
  "<your api endpoint url>" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [
      "Tell me a joke"
    ],
    "temperature": 0.8,
    "max_tokens": 2048
  }'
```

The API will attempt to invoke the Bedrock models in order as defined in config/models.yaml, with automatic fallback if a model or region is unavailable.