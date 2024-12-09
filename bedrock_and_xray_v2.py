import json
import boto3
import traceback
from aws_xray_sdk.core import xray_recorder, patch
import logging


logging.basicConfig(level='WARNING')
logging.getLogger('aws_xray_sdk').setLevel(logging.INFO)

# Configure X-Ray
xray_recorder.configure(
    sampling=False,
    context_missing='LOG_ERROR',
    daemon_address='127.0.0.1:3000',
    dynamic_naming='*mysite.com*'
)

# Patch AWS SDK
patch(["boto3"])

def invoke_bedrock():
    # Initialize Bedrock client
    bedrock = boto3.client('bedrock-runtime')
    
    # Create a segment
    with xray_recorder.in_segment('bedrock_request') as segment:
    
        try:
            # Create subsegment for the API call
            with xray_recorder.in_subsegment('bedrock_inference') as subsegment:
                response = bedrock.invoke_model(
                    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "messages": [
                            {
                                "role": "user",
                                "content": "Hello, how are you?"
                            }
                        ],
                        "max_tokens": 100
                    })
                )
                
                subsegment.put_metadata('model', 'anthropic.claude-3-sonnet')
                subsegment.put_annotation('status', 'success')
                
                # Process response if needed
                print(json.loads(response['body'].read()))
                
        except Exception as e:
            if xray_recorder.current_subsegment():
                stack = traceback.extract_stack()
                xray_recorder.current_subsegment().add_exception(e, stack)
            raise


if __name__ == "__main__":
    invoke_bedrock()
