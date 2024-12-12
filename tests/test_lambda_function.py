import json


def test_missing_contents():
    """Test lambda handler with missing contents"""
    from src.lambda_function import lambda_handler

    event = {
        "body": json.dumps({
            "max_tokens": 100,
            "temperature": 0.7
        })
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": "No prompt provided"}

def test_lambda_handler_success():
    """Test successful lambda handler execution"""
    from src.lambda_function import lambda_handler

    # Prepare test data
    event = {
        "body": json.dumps({
            "contents": ["Hello"],
            "max_tokens": 100,
            "temperature": 0.7
        })
    }
    
    # Execute test
    response = lambda_handler(event, None)

    # Verify response
    print(response)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"]["role"] == "assistant"
