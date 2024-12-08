# Amazon Bedrock Redundant API

This project provides a production-ready solution for handling redundant model invocations across regions using Amazon Bedrock through AWS Lambda and API Gateway, with built-in rate limit handling and streaming support.

## Features

- Handles rate limiting across multiple models and regions
- Configurable retry mechanism
- Easy model configuration through YAML
- AWS CDK infrastructure as code
- Comprehensive test coverage

## Project Structure

```
.
├── config/
│   └── models.yaml         # Model configuration
├── infrastructure/
│   ├── app.py             # CDK app entry point
│   └── bedrock_stack.py   # CDK stack definition
├── src/
│   └── lambda_function.py # Lambda handler implementation
├── tests/
│   └── test_lambda_function.py # Unit tests
├── .pre-commit-config.yaml # Pre-commit hooks configuration
├── pyproject.toml         # Project dependencies and config
└── README.md             # Project documentation
```

## Setup

1. Create and activate virtual environment:
```bash
uv venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
uv sync
```

3. Install pre-commit hooks:
```bash
pre-commit install
```

## Development

1. Update model configuration in `config/models.yaml`
2. Run tests:
```bash
pytest
```

3. Deploy infrastructure:
```bash
cdk deploy --context account=YOUR_ACCOUNT_ID --context region=YOUR_REGION
```

## Usage

Send POST request to the API Gateway endpoint:

```bash
curl -X POST https://your-api-endpoint.execute-api.region.amazonaws.com/prod/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Your prompt here"}'
```

## Contributing

1. Ensure all tests pass
2. Run pre-commit hooks before committing:
```bash
pre-commit run --all-files
```