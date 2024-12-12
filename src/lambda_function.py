import json
import logging
import os
import time
from typing import Any, Dict, Optional

import boto3
import yaml
from aws_xray_sdk.core import xray_recorder
from botocore.exceptions import ClientError

logger = logging.getLogger("amazon_bedrock_redundant_api")
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Configure X-Ray
xray_recorder.configure(
    sampling=False,
    context_missing='LOG_ERROR'
)

models = []
with open(os.environ.get('CONFIG_FILE_PATH')) as f:
    models = yaml.safe_load(f)['models']
regions = {region for model in models for region in model.get("regions", [])}

clients = {
    region: boto3.client("bedrock-runtime", region_name=region)
    for region in regions
}

@xray_recorder.capture("invoke_model")
def invoke_model(
    client: Any,
    model_id: str,
    contents: list[str],
    max_tokens: int,
    temperature: float
) -> Optional[Dict[str, Any]]:

    subsegment = xray_recorder.current_subsegment()
    subsegment.put_metadata('model_id', model_id)
    subsegment.put_metadata('contents', contents)
    subsegment.put_metadata('max_tokens', max_tokens)
    subsegment.put_metadata('temperature', temperature)

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
        if e.response["Error"]["Code"] in ("ThrottlingException", "ServiceQuotaExceededException"):
            logger.warning(f"Rate limit hit for model {model_id} in {client.meta.region_name}.")
            return None
        raise

@xray_recorder.capture('inference_manager')
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Segment is automatically created by X-Ray
    subsegment = xray_recorder.current_subsegment()

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

        for model_rank, model in enumerate(models):
            model_id = model.get("model_id")
            regions = model.get("regions", [])
            max_retries = model.get("max_retries", 2)
            retry_delay = model.get("retry_delay", 2)

            for region_rank, region in enumerate(regions):
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
                        _n = _retry + 1
                        logger.warning(
                            f"Retry {model.get('name')} in {region} {_n}/{max_retries} times.")
                        time.sleep(retry_delay)
                # Break if response is not None after retry
                if response is not None:
                    break
            # Break if response is not None after switching region
            if response is not None:
                break

        subsegment.put_annotation('model_rank', model_rank + 1)
        subsegment.put_annotation('region_rank', region_rank + 1)

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
