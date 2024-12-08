import json
import logging
import os
import time
from typing import Any, Dict, Optional

import boto3
import yaml
from botocore.exceptions import ClientError

logger = logging.getLogger("amazon-bedrock-redundant-api")
logger.setLevel(logging.INFO)

def load_model_config() -> Dict[str, Any]:
    config_path = os.path.join(os.path.dirname(__file__), "../config/models.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

config = load_model_config()
models = config.get("models", [])
regions = {region for model in models for region in model.get("regions", [])}

clients = {
    region: boto3.client("bedrock-runtime", region_name=region)
    for region in regions
}

def invoke_model(
    client: Any,
    model_id: str,
    contents: list[str],
    max_tokens: int,
    temperature: float
) -> Optional[Dict[str, Any]]:
    try:
        response = client.converse(
            modelId=model_id,
            messages=[{
                "role": (("user" if i % 2 == 0 else "assistant")),
                "content": [{"text": content}]
            } for i, content in enumerate(contents)],
            inferenceConfig={
                "temperature": temperature,
                "maxTokens": max_tokens
            }
        )
        return response
    except ClientError as e:
        if e.response["Error"]["Code"] == "ThrottlingException":
            logger.warning(f"Rate limit hit for model {model_id} in {client.meta.region_name}.")
            return None
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        contents = event.get("contents")
        if not contents:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No prompt provided"})
            }

        temperature = event.get("temperature", 0.7)
        max_tokens = event.get("max_tokens", 1024)
        response = None

        for model in models:
            model_id = model.get("model_id")
            regions = model.get("regions", [])
            max_retries = model.get("max_retries", 2)
            retry_delay = model.get("retry_delay", 2)

            for region in regions:
                client = clients[region]
                for _retry in range(max_retries):
                    response = invoke_model(
                        client,
                        model_id,
                        contents,
                        max_tokens,
                        temperature
                    )
                    if response is not None:
                        break
                    else:
                        time.sleep(retry_delay)
                logger.warning(f"Max retries reached for {model.get('name')} in {region}.")
            
            if response is not None:
                break
            logger.warning(f"Max retries reached for {model.get('name')}.")

        if response is not None:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": response["output"]["message"]})
            }
        else:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Rate limit hit for all models"})
            }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }