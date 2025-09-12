"""DynamoDB table for session management. Owner sessions and finder sessions in different tables."""

from aws_cdk import Stack, RemovalPolicy
from aws_cdk.aws_dynamodb import Table, Attribute, AttributeType, BillingMode

class SessionStack(Stack):
    def __init__(self, scope, construct_id, stage="dev",**kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.session_table = Table(
            self, f"OwnerSessionTable-{stage}",
            partition_key=Attribute(name="session_token", type=AttributeType.STRING),
            removal_policy=RemovalPolicy.RETAIN,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",   # Privacy: TTL auto-cleanup
        )

        self.finder_session_table = Table(
            self, f"FinderSessionTable-{stage}",
            partition_key=Attribute(name="session_token", type=AttributeType.STRING),
            removal_policy=RemovalPolicy.RETAIN,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",   # Privacy: TTL auto-cleanup
        )
        