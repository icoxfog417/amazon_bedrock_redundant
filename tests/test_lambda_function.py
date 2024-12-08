import json  # noqa: I001
import os
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


test_config = {
    "models": [
        {
            "model_id": "test-model",
            "name": "Test Model",
            "regions": ["us-east-1", "us-west-2"],
            "max_retries": 2,
            "retry_delay": 1
        }
    ]
}
os.environ["MODEL_CONFIG"] = json.dumps(test_config)

from src.lambda_function import lambda_handler  # noqa: E402


@pytest.fixture()
def mock_env_config():
    """Fixture to provide test model configuration."""
    return test_config


def test_missing_contents():
    """Test lambda handler with missing contents."""
    event = {
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": "No prompt provided"}

def test_lambda_handler_success(mock_env_config):
    """Test successful lambda handler with environment configuration."""
    event = {
        "contents": ["Hello"],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    with patch("src.lambda_function.boto3.client") as mock_boto3_client:
        mock_client = MagicMock()
        mock_response = {
            "output": {
                "message": "Test response"
            }
        }
        mock_client.converse.return_value = mock_response
        mock_boto3_client.return_value = mock_client
        
        response = lambda_handler(event, None)
        print(response)
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == {"message": "Test response"}

def test_lambda_handler_retry(mock_env_config):
    """Test lambda handler with region retry and failover."""
    event = {
        "contents": ["Hello"],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    with patch("src.lambda_function.boto3.client") as mock_boto3_client, \
         patch("src.lambda_function.time.sleep") as mock_sleep:
        mock_client_east = MagicMock()
        mock_client_west = MagicMock()
        
        # First region fails with throttling
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        mock_client_east.converse.side_effect = ClientError(error_response, "converse")
        mock_client_east.meta.region_name = "us-east-1"
        
        # Second region succeeds
        mock_response = {
            "output": {
                "message": "Test response"
            }
        }
        mock_client_west.converse.return_value = mock_response
        mock_client_west.meta.region_name = "us-west-2"
        
        # Return different clients based on region
        def get_client(service, region_name):
            if region_name == "us-east-1":
                return mock_client_east
            return mock_client_west
            
        mock_boto3_client.side_effect = get_client
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == {"message": "Test response"}
        mock_sleep.assert_called()  # Verify retry delay was used

def test_lambda_handler_exception():
    """Test lambda handler with unexpected exception."""
    event = {
        "contents": ["Hello"],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    with patch("src.lambda_function.boto3.client") as mock_boto3_client:
        mock_client = MagicMock()
        mock_client.converse.side_effect = Exception("Unexpected error")
        mock_boto3_client.return_value = mock_client
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 500
        assert "error" in json.loads(response["body"])

def test_lambda_handler_multiple_models(mock_env_config):
    """Test lambda handler with multiple models in config."""
    # Update config to include multiple models
    mock_env_config["models"].append({
        "model_id": "backup-model",
        "name": "Backup Model",
        "regions": ["us-west-2"],
        "max_retries": 1,
        "retry_delay": 1
    })
    
    event = {
        "contents": ["Hello"],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    with patch("src.lambda_function.boto3.client") as mock_boto3_client, \
         patch("src.lambda_function.time.sleep"):
        mock_client_primary = MagicMock()
        mock_client_backup = MagicMock()
        
        # Primary model fails
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        mock_client_primary.converse.side_effect = ClientError(error_response, "converse")
        mock_client_primary.meta.region_name = "us-east-1"
        
        # Backup model succeeds
        mock_response = {
            "output": {
                "message": "Backup response"
            }
        }
        mock_client_backup.converse.return_value = mock_response
        mock_client_backup.meta.region_name = "us-west-2"
        
        def get_client(service, region_name):
            return mock_client_backup if region_name == "us-west-2" else mock_client_primary
            
        mock_boto3_client.side_effect = get_client
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == {"message": "Backup response"}

def test_lambda_handler_all_regions_fail(mock_env_config):
    """Test lambda handler when all regions fail."""
    event = {
        "contents": ["Hello"],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    with patch("src.lambda_function.boto3.client") as mock_boto3_client, \
         patch("src.lambda_function.time.sleep"):
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded"
            }
        }
        mock_client = MagicMock()
        mock_client.converse.side_effect = ClientError(error_response, "converse")
        mock_client.meta.region_name = "us-east-1"
        mock_boto3_client.return_value = mock_client
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 500
        assert json.loads(response["body"]) == {"error": "Rate limit hit for all models"}
