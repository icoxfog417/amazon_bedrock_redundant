import json
import aws_cdk as cdk
import yaml

from infrastructure.bedrock_stack import AmazonBedrockRedundantAPI

with open('config/models.yaml', 'r') as file:
    config = yaml.safe_load(file)

app = cdk.App()
AmazonBedrockRedundantAPI(app, "AmazonBedrockRedundantAPI",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region"),
    ),
    environment_variables={
        "MODEL_CONFIG": json.dumps(config)
    }
)

app.synth()
