import json
import logging
import os
import time
from typing import Any, Dict, Optional

import boto3
from aws_xray_sdk.core import xray_recorder, patch
from botocore.exceptions import ClientError

logger = logging.getLogger("amazon-bedrock-redundant-api")
logger.setLevel(logging.INFO)

# Configure X-Ray
xray_recorder.configure(
    sampling=False,
    context_missing='LOG_ERROR',
    daemon_address='127.0.0.1:3000',
)
patch(["boto3"])

config = json.loads(os.environ.get("MODEL_CONFIG", "{}"))
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
        logger.info(f"Got response from {model_id} in {client.meta.region_name}.")
        return response
    except ClientError as e:
        if e.response["Error"]["Code"] == "ThrottlingException":
            logger.warning(f"Rate limit hit for model {model_id} in {client.meta.region_name}.")
            return None
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        logger.info(f"Got event:\n {event}")
        body = json.loads(event.get("body", '{}'))
        contents = body.get("contents")
        if not contents:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No prompt provided"})
            }

        temperature = body.get("temperature", 0.7)
        max_tokens = body.get("max_tokens", 1024)
        response = None

        for model in models:
            model_id = model.get("model_id")
            regions = model.get("regions", [])
            max_retries = model.get("max_retries", 2)
            retry_delay = model.get("retry_delay", 2)
            with xray_recorder.in_segment(f'bedrock-request') as segment:
                segment.put_annotation('model_id', model_id)
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
                        # Retry if rate limit hit
                        if response is not None:
                            break
                        else:
                            logger.warning(f"Retry {model.get('name')} in {region} {_retry + 1}/{max_retries} times.")
                            time.sleep(retry_delay)
                    # Break if response is not None
                    if response is not None:
                        break
            # Break if response is not None
            if response is not None:
                break
            logger.warning(f"Switch next model...")

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
