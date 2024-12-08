#!/usr/bin/env python3
import aws_cdk as cdk

from infrastructure.bedrock_stack import AmazonBedrockRedundantAPI

app = cdk.App()
AmazonBedrockRedundantAPI(app, "AmazonBedrockRedundantAPI",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region")
    )
)

app.synth()
