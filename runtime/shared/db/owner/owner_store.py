"""DynamoDB client for Owner records with Pydantic validation."""

import os
from typing import Optional, Any, Dict, TYPE_CHECKING

import boto3
from pydantic import ValidationError, create_model, Field
from botocore.exceptions import ClientError

from shared.db.owner.owner_model import Owner, State, PasswordHash, PublicKey, Timestamp,OwnerHash

from shared.com.logging_utils import ProjectLogger
from shared.com.shared_helper import current_unix_timestamp_utc, dynamodb_decimal_to_int

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table, DynamoDBServiceResource

logger = ProjectLogger(__name__).get_logger()

# type: ignore[call-arg]
# pylance: disable=reportCallIssue
# Note: Linter false positive - Pydantic v2 dynamic create_model("TempModel", ...) works, but Pylance has missing dynamic typing support for this usage.


class OwnerHelper:
    """Utility functions for working with Owner model (no DB, no crypto)."""

    @staticmethod
    def create_owner(  # pylint: disable=too-many-arguments
        *,  # factory method, keywords only
        owner_hash: str,
        salt: str,
        password_hash: str,
        public_key: str,
        random_entropy: str,
        created_at: Optional[int] = None,
        owner_encrypted_storage: Optional[str] = "",
        state: State = State.ONBOARDING,
    ) -> Owner:
        """Creates a validated Owner object from fields, raises ValidationError if invalid."""
        _state = State(state) if isinstance(state, str) else state
        return Owner(
            owner_hash=OwnerHash(value=owner_hash),
            salt=salt,
            password_hash=PasswordHash(value=password_hash),
            public_key=PublicKey(value=public_key),
            random_entropy=random_entropy,
            owner_encrypted_storage=owner_encrypted_storage or "",
            created_at=Timestamp(value=created_at or current_unix_timestamp_utc()),
            state=_state
        )

    @staticmethod
    def is_active(owner: Owner) -> bool:
        return owner.state == State.ACTIVE

    @staticmethod
    def is_blocked(owner: Owner) -> bool:
        return owner.state == State.BLOCKED

    @staticmethod
    def is_in_deletion(owner: Owner) -> bool:
        return owner.state == State.IN_DELETION

    @staticmethod
    def validate_owner(owner: Owner) -> bool:
        """Returns True if the Owner object is valid, False otherwise."""
        try:
            owner.model_validate(owner.model_dump())
            return True
        except ValidationError:
            logger.error("Owner validation error")
            return False

    # Single-field validation via Pydantic V2
    @staticmethod
    def validate_field(field_name: str, value) -> bool:
        """Uses Pydantic V2 to validate a single field of Owner, including constraints."""
        try:
            field_info = Owner.model_fields[field_name]
            field_type = field_info.annotation
            field_constraints = field_info.metadata
            # Build Field with constraints if present
            field_args = {}
            for k in ["min_length", "max_length", "pattern"]:
                if k in field_constraints:
                    field_args[k] = field_constraints[k]
            temp_field = Field(**field_args) if field_args else ...
            temp_model = create_model("TempModel", **{field_name: (field_type, temp_field)})
            temp_model.model_validate({field_name: value})
            return True
        except ValidationError:
            logger.error(f"Owner field validation error: {field_name}")
            return False


class OwnerStore:
    """DynamoDB client for Owner records with Pydantic validation."""

    def __init__(self, table_name: Optional[str] = None, ddb_resource: Optional[Any] = None):
        """
        Owner DB client for accessing Owner records in DynamoDB.
        :param table_name: DynamoDB table name for owners.
        :param ddb_resource: boto3 resource (for mocking/testing).
        """
        self.table_name = table_name or os.environ.get("OWNER_TABLE_NAME", "LostAndFound-Owner")
        self.ddb: DynamoDBServiceResource = ddb_resource or boto3.resource("dynamodb")
        self.table: Table = self.ddb.Table(self.table_name)

    def create_owner(self, owner: Owner):
        """Create a new owner; fails if the owner_hash already exists."""
        item = owner.model_dump(mode="json", exclude_unset=True)
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(owner_hash)")
        except ClientError as e:
            logger.error(f"create_owner client error: {e}")
            raise

    def get_owner(self, owner_hash: str) -> Optional[Owner]:
        """Read all fields of an owner; returns validated Owner or None if not found."""
        try:
            response = self.table.get_item(Key={"owner_hash": owner_hash if isinstance(owner_hash, str) else owner_hash.value})
            item = response.get("Item")
            if item:
                item = dynamodb_decimal_to_int(item)
                # Wrap identifier fields for model validation
                if "owner_hash" in item:
                    item["owner_hash"] = OwnerHash(value=item["owner_hash"])
                if "password_hash" in item:
                    item["password_hash"] = PasswordHash(value=item["password_hash"])
                if "public_key" in item:
                    item["public_key"] = PublicKey(value=item["public_key"])
                if "created_at" in item:
                    item["created_at"] = Timestamp(value=item["created_at"])
            return Owner.model_validate(item) if item else None
        except ClientError:
            return None
        except ValidationError as e:
            logger.error(f"get_owner validation error: {e}")
            return None
        except Exception as e:
            logger.error(f"get_owner unknown error: {e}")
            return None

    def get_owner_field(self, owner_hash: str, field: str) -> Optional[Any]:
        """Read a single field of an owner document."""
        try:
            expr_names = {f"#{field}": field}
            response = self.table.get_item(Key={"owner_hash": owner_hash}, ProjectionExpression=f"#{field}", ExpressionAttributeNames=expr_names)
            item = response.get("Item")
            if item and field in item:
                return item[field]
            return None
        except ClientError as e:
            logger.error(f"get_owner_field client error: {e}")
            return None
        except Exception as e:  #pylint: disable=broad-except
            logger.error(f"get_owner_field unknown error: {e}")
            return None

    def put_owner(self, owner: Owner) -> None:
        """Create or overwrite the entire owner record."""
        try:
            item = owner.model_dump()
            # DynamoDB expects string for key fields, not dicts
            item["owner_hash"] = owner.owner_hash.value
            item["password_hash"] = owner.password_hash.value
            item["public_key"] = owner.public_key.value
            item["created_at"] = owner.created_at.value
            item["salt"] = owner.salt
            item["random_entropy"] = owner.random_entropy
            item["owner_encrypted_storage"] = owner.owner_encrypted_storage
            item["state"] = owner.state.value if hasattr(owner.state, "value") else owner.state
            self.table.put_item(Item=item)
        except Exception as e:
            logger.error(f"put_owner error: {e}")
            raise

    def update_owner_field(self, owner_hash: str, field: str, value: Any):
        """Update a single field for an existing owner."""
        if field not in Owner.ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"field >{field}< not part of Owner")
        key_value = owner_hash.value if hasattr(owner_hash, "value") else owner_hash
        resp = self.table.update_item(
            Key={"owner_hash": key_value},
            UpdateExpression="SET #field = :val",
            ExpressionAttributeNames={"#field": field},
            ExpressionAttributeValues={":val": value},
        )
        return resp

    def update_owner_fields(self, owner_hash: str, updates: Dict[str, Any]):
        """Update multiple fields for an existing owner."""
        expr_names = {f"#{k}": k for k in updates}
        expr = "SET " + ", ".join(f"#{k}=:{k}" for k in updates)
        attrs = {f":{k}": v for k, v in updates.items()}
        try:
            resp = self.table.update_item(Key={"owner_hash": owner_hash},
                                          UpdateExpression=expr,
                                          ExpressionAttributeValues=attrs,
                                          ExpressionAttributeNames=expr_names,
                                          ReturnValues="UPDATED_NEW")
            return resp.get("Attributes")
        except Exception as e:
            logger.error(f"update_owner_fields error: {e}")
            raise

    def delete_owner(self, owner_hash: str):
        """Delete the owner record from the database."""
        try:
            self.table.delete_item(Key={"owner_hash": owner_hash})
        except ClientError as e:
            logger.error(f"delete_owner error: {e}")
            raise
