"""CDK stack for static assets (frontend)"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
)
from aws_cdk.aws_s3 import BlockPublicAccess, BucketAccessControl, BucketEncryption

from constructs import Construct


class UIStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, stage="dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for static assets (frontend)
        bucket = s3.Bucket(self,
                           f"LostAndFoundStaticAssets-{stage}",
                           removal_policy=RemovalPolicy.RETAIN,
                           website_error_document="404.html",
                           website_index_document="index.html",
                           block_public_access=BlockPublicAccess.BLOCK_ACLS_ONLY,
                           public_read_access=True,
                           access_control=BucketAccessControl.PUBLIC_READ,
                           encryption=BucketEncryption.S3_MANAGED)

        CfnOutput(self, "StaticAssetsBucketName", value=bucket.bucket_name)
