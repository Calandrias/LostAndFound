"""Owner related infra stack"""

from aws_cdk import Stack, RemovalPolicy
from aws_cdk.aws_dynamodb import (Table, Attribute, AttributeType, BillingMode)


class OwnerStack(Stack):
    """Owner Stack with DynamoDB table for owner data."""

    def __init__(self, scope, construct_id, stage="dev", **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        self.owner_table = Table(self,
                                 f"OwnerTable-{stage}",
                                 partition_key=Attribute(name="owner_hash", type=AttributeType.STRING),
                                 billing_mode=BillingMode.PAY_PER_REQUEST,
                                 removal_policy=RemovalPolicy.RETAIN)
