from aws_cdk import (
    Duration,
    Stack,
)
from aws_cdk import (
    aws_apigateway as apigw,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from constructs import Construct


class AmazonBedrockRedundantAPI(Stack):
    def __init__(self, scope: Construct, construct_id: str, environment_variables:dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda function
        lambda_role = iam.Role(
            self, "BedrockLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AWSXRayDaemonWriteAccess"
            )
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=["*"]
            )
        )

        handler = _lambda.Function(
            self, "BedrockHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset(
                "src",
                bundling={
                    "image": _lambda.Runtime.PYTHON_3_11.bundling_image,
                    "command": ["bash", "-c", 
                                "pip install -r requirements.txt -t /tmp/deps && cp -au . /tmp/deps"],
                    "user": "root"
                }),
            handler="lambda_function.lambda_handler",
            environment= environment_variables,
            timeout=Duration.seconds(30),
            memory_size=256,
            role=lambda_role,
            tracing=_lambda.Tracing.ACTIVE
        )

        # Create API Gateway
        api = apigw.RestApi(
            self, "BedrockAPI",
            rest_api_name="Amazon Bedrock Redundant API",
            description="API for handling redundant model invocations across regions",
            deploy_options=apigw.StageOptions(
                stage_name="v1",
                tracing_enabled=True
            )
        )

        integration = apigw.LambdaIntegration(
            handler,
            request_templates={"application/json": '{ "statusCode": "200" }'}
        )

        api.root.add_method(
            "POST",
            integration,
            api_key_required=False,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigw.Model.EMPTY_MODEL
                    }
                ),
                apigw.MethodResponse(
                    status_code="400",
                    response_models={
                        "application/json": apigw.Model.ERROR_MODEL
                    }
                ),
                apigw.MethodResponse(
                    status_code="429",
                    response_models={
                        "application/json": apigw.Model.ERROR_MODEL
                    }
                ),
                apigw.MethodResponse(
                    status_code="500",
                    response_models={
                        "application/json": apigw.Model.ERROR_MODEL
                    }
                ),
            ]
        )