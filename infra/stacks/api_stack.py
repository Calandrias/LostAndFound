from pathlib import Path
from typing import cast
from dataclasses import dataclass

from aws_cdk import (Stack, Duration)
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_lambda import LayerVersion, Function, Runtime, Code
from constructs import Construct


def find_path_recursively(local_path: Path, key: str):
    """Find a directory with the given key by searching upwards recursively.
    it checks all folders in the current path and then goes one level up until it finds the key or reaches the root.
    Raises FileNotFoundError if the key is not found."""
    current_path = local_path.resolve()
    while True:
        if (current_path / key).exists():
            return current_path / key
        if current_path.parent == current_path:
            raise FileNotFoundError(f"Could not find {key} in any parent directories of {local_path}")
        current_path = current_path.parent


@dataclass
class ApiStackResources:
    """A bag to pass resources between stacks."""
    owner_table: Table
    tag_table: Table
    owner_session_table: Table
    finder_session_table: Table


class AttrDict(dict):

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class ApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, resources_bag: ApiStackResources, stage="dev", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        shared_layer = LayerVersion.from_layer_version_arn(self,
                                                           f"SharedLayer-{stage}",
                                                           layer_version_arn=f"arn:aws:lambda:{self.region}:{self.account}:layer:LostAndFoundSharedLayer:1")

        self.lambdas = AttrDict()
        runtime_path = find_path_recursively(Path(__file__), 'runtime')

        self.lambdas.onboarding = cast(
            Function,
            Function(
                self,
                id=f"OnboardingFunction-{stage}",
                runtime=Runtime.PYTHON_3_12,
                code=Code.from_asset(str(runtime_path.joinpath("onboarding").resolve())),
                handler="onboarding.lambda_handler",
                environment={
                    "OWNER_TABLE_NAME": resources_bag.owner_table.table_name,
                    "OWNER_SESSION_TABLE_NAME": resources_bag.owner_session_table.table_name,
                },
                layers=[shared_layer],
                memory_size=128,
                timeout=Duration.seconds(3),
            ))

        resources_bag.owner_table.grant_read_write_data(self.lambdas.onboarding)
        resources_bag.owner_session_table.grant_read_write_data(self.lambdas.onboarding)

        self.lambdas.login = cast(
            Function,
            Function(
                self,
                id=f"LoginFunction-{stage}",
                runtime=Runtime.PYTHON_3_12,
                code=Code.from_asset(str(runtime_path.joinpath("login").resolve())),
                handler="login.lambda_handler",
                environment={
                    "OWNER_TABLE_NAME": resources_bag.owner_table.table_name,
                    "OWNER_SESSION_TABLE_NAME": resources_bag.owner_session_table.table_name,
                },
                layers=[shared_layer],
                memory_size=128,
                timeout=Duration.seconds(3),
            ))
        resources_bag.owner_table.grant_read_data(self.lambdas.login)
        resources_bag.owner_session_table.grant_read_write_data(self.lambdas.login)
