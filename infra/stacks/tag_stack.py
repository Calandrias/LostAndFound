"""
QR Tag related resources
"""

from aws_cdk import Stack, RemovalPolicy
from aws_cdk.aws_dynamodb import (Table, Attribute, AttributeType, BillingMode)


class TagStack(Stack):

    def __init__(self, scope, construct_id, stage="dev", **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        self.tag_table = Table(self,
                               f"TagTable-{stage}",
                               partition_key=Attribute(name="tag_id", type=AttributeType.STRING),
                               billing_mode=BillingMode.PAY_PER_REQUEST,
                               removal_policy=RemovalPolicy.RETAIN)
