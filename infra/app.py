#!/usr/bin/env python3

import os
import aws_cdk as cdk

from infra.stacks import (
    ApiStackResources,
    ApiStack,
    UIStack,
    OwnerStack,
    SessionStack,
    TagStack,
)

stage = os.getenv("STAGE", "dev")  # Default 'dev'
region = os.getenv("CDK_DEFAULT_REGION", "eu-central-1")
account = os.getenv("CDK_DEFAULT_ACCOUNT", "123456789012")

env = cdk.Environment(account=account, region=region)

app = cdk.App()

owner = OwnerStack(scope=app, construct_id=f"LostAndFoundOwnerStack-{stage}", env=env, stage=stage)
session = SessionStack(scope=app, construct_id=f"LostAndFoundSessionStack-{stage}", env=env, stage=stage)
tags = TagStack(scope=app, construct_id=f"LostAndFoundTagStack-{stage}", env=env, stage=stage)

resources_bag = ApiStackResources(
    owner_table=owner.owner_table,
    tag_table=tags.tag_table,  # Not used in API stack
    owner_session_table=session.session_table,
    finder_session_table=session.finder_session_table,
)

api = ApiStack(scope=app, construct_id=f"LostAndFoundApiStack-{stage}", env=env, resources_bag=resources_bag, stage=stage)

ui = UIStack(scope=app, construct_id=f"LostAndFoundUIStack-{stage}", env=env, stage=stage)

app.synth()
