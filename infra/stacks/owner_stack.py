"""Owner related infra stack"""

from aws_cdk import Stack, RemovalPolicy
from aws_cdk.aws_dynamodb import (Table, Attribute, AttributeType, BillingMode)


class OwnerStack(Stack):
    def __init__(self, scope, construct_id, stage="dev",**kwargs):
        super().__init__(scope, construct_id, **kwargs)
        self.owner_table = Table(
            self, f"OwnerTable-{stage}",
            partition_key=Attribute(name="owner_hash", type=AttributeType.STRING),
            billing_mode=BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN
        )
