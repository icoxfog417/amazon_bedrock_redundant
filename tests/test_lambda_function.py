import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from src.lambda_function import lambda_handler, load_model_config, invoke_model

def test_load_model_config():
    """Test loading model configuration."""
    config = load_model_config()
    assert "models" in config
    assert isinstance(config["models"], list)

def test_invoke_model_success():
    """Test successful model invocation."""
    mock_client = MagicMock()
    mock_response = {
        "messages": [{"content": "Test response"}]
    }
    mock_client.converse.return_value = mock_response
    
    result = invoke_model(
        client=mock_client,
        model_id="test-model",
        contents=["Hello", "Hi there"],
        max_tokens=100,
        temperature=0.7
    )
    
    mock_client.converse.assert_called_once_with(
        modelId="test-model",
        messages=[
            {"role": "user", "content": [{"text": "Hello"}]},
            {"role": "assistant", "content": [{"text": "Hi there"}]}
        ],
        inferenceConfig={
            "temperature": 0.7,
            "maxTokens": 100
        }
    )
    assert result == mock_response

def test_invoke_model_throttling():
    """Test model invocation with throttling exception."""
    mock_client = MagicMock()
    error_response = {
        "Error": {
            "Code": "ThrottlingException",
            "Message": "Rate exceeded"
        }
    }
    mock_client.converse.side_effect = ClientError(error_response, "converse")
    mock_client.meta.region_name = "us-east-1"
    
    result = invoke_model(
        client=mock_client,
        model_id="test-model",
        contents=["Test"],
        max_tokens=100,
        temperature=0.7
    )
    
    assert result is None
