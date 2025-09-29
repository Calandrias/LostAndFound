"""
DynamoDB client for Owner records with Pydantic validation.

All public methods and classes are fully typed and documented. All exceptions that may be raised are documented in the docstrings.
"""

import os
from typing import Optional, Any, Dict, TYPE_CHECKING

import boto3
from pydantic import ValidationError, create_model, Field
from botocore.exceptions import ClientError

from shared.db.owner.owner_model import Owner, State, PasswordHash, PublicKey, Timestamp, OwnerHash

from shared.com.logging_utils import ProjectLogger
from shared.com.shared_helper import current_unix_timestamp_utc, dynamodb_decimal_to_int

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table, DynamoDBServiceResource

logger = ProjectLogger(__name__).get_logger()

# type: ignore[call-arg]
# pylance: disable=reportCallIssue
# Note: Linter false positive - Pydantic v2 dynamic create_model("TempModel", ...) works, but Pylance has missing dynamic typing support for this usage.


class OwnerHelper:
    """
    Utility functions for working with Owner model (no DB, no crypto).
    """

    @staticmethod
    def create_owner(
        *,
        owner_hash: str,
        salt: str,
        password_hash: str,
        public_key: str,
        random_entropy: str,
        created_at: Optional[int] = None,
        owner_encrypted_storage: Optional[str] = "",
        state: State = State.ONBOARDING,
    ) -> Owner:
        """
        Creates a validated Owner object from fields.

        Args:
            owner_hash (str): Unique owner hash.
            salt (str): Salt for password hashing.
            password_hash (str): Hashed password.
            public_key (str): Public key string.
            random_entropy (str): Random entropy for owner.
            created_at (Optional[int]): Creation timestamp (UTC, seconds).
            owner_encrypted_storage (Optional[str]): Encrypted storage blob.
            state (State): Owner state (default: ONBOARDING).

        Returns:
            Owner: Validated Owner object.

        Raises:
            ValidationError: If any field is invalid.
        """
        _state = State(state) if isinstance(state, str) else state
        return Owner(owner_hash=OwnerHash(value=owner_hash),
                     salt=salt,
                     password_hash=PasswordHash(value=password_hash),
                     public_key=PublicKey(value=public_key),
                     random_entropy=random_entropy,
                     owner_encrypted_storage=owner_encrypted_storage or "",
                     created_at=Timestamp(value=created_at or current_unix_timestamp_utc()),
                     state=_state)

    @staticmethod
    def is_active(owner: Owner) -> bool:
        """
        Checks if the owner is active.

        Args:
            owner (Owner): Owner object.
        Returns:
            bool: True if active, False otherwise.
        """
        return owner.state == State.ACTIVE

    @staticmethod
    def is_blocked(owner: Owner) -> bool:
        """
        Checks if the owner is blocked.

        Args:
            owner (Owner): Owner object.
        Returns:
            bool: True if blocked, False otherwise.
        """
        return owner.state == State.BLOCKED

    @staticmethod
    def is_in_deletion(owner: Owner) -> bool:
        """
        Checks if the owner is in deletion state.

        Args:
            owner (Owner): Owner object.
        Returns:
            bool: True if in deletion, False otherwise.
        """
        return owner.state == State.IN_DELETION

    @staticmethod
    def validate_owner(owner: Owner) -> bool:
        """
        Validates the Owner object.

        Args:
            owner (Owner): Owner object.
        Returns:
            bool: True if valid, False otherwise.
        Raises:
            ValidationError: If validation fails.
        """
        try:
            owner.model_validate(owner.model_dump())
            return True
        except ValidationError:
            logger.error("Owner validation error")
            return False

    @staticmethod
    def validate_field(field_name: str, value: Any) -> bool:
        """
        Uses Pydantic to validate a single field of Owner, including constraints.

        Args:
            field_name (str): Name of the field to validate.
            value (Any): Value to validate.
        Returns:
            bool: True if valid, False otherwise.
        Raises:
            ValidationError: If validation fails.
            KeyError: If field does not exist.
            TypeError: If type is invalid.
            ValueError: If value is invalid.
        """
        try:
            # Owner.model_fields is a dict of ModelField, see https://pydantic.dev/latest/usage/models/#model-fields
            field_info = Owner.model_fields[field_name]  # type: ignore # pylint: disable=unsubscriptable-object
            field_type = field_info.annotation
            field_constraints = field_info.metadata
            field_args = {}
            for k in ["min_length", "max_length", "pattern"]:
                if k in field_constraints:
                    field_args[k] = field_constraints[k]
            temp_field = Field(**field_args) if field_args else ...
            temp_model = create_model("TempModel", **{field_name: (field_type, temp_field)})
            temp_model.model_validate({field_name: value})
            return True
        except (ValidationError, KeyError, TypeError, ValueError) as e:
            logger.error(f"Owner field validation error: {field_name}, value={value}, error={e}")
            return False


class OwnerStore:
    """
    DynamoDB client for Owner records with Pydantic validation.

    Methods raise ClientError for AWS issues, ValidationError for model issues, and ValueError for invalid field updates.
    """

    def __init__(self, table_name: Optional[str] = None, ddb_resource: Optional[Any] = None):
        """
        Owner DB client for accessing Owner records in DynamoDB.

        Args:
            table_name (Optional[str]): DynamoDB table name for owners.
            ddb_resource (Optional[Any]): boto3 resource (for mocking/testing).
        """
        self.table_name = table_name or os.environ.get("OWNER_TABLE_NAME", "LostAndFound-Owner")
        self.ddb: DynamoDBServiceResource = ddb_resource or boto3.resource("dynamodb")
        self.table: Table = self.ddb.Table(self.table_name)

    def create_owner(self, owner: Owner) -> None:
        """
        Create a new owner; fails if the owner_hash already exists.

        Args:
            owner (Owner): Owner object to create.
        Raises:
            ClientError: If DynamoDB put_item fails (e.g., duplicate owner_hash).
        """
        item = owner.model_dump(mode="json", exclude_unset=True)
        item["owner_hash"] = owner.owner_hash.value
        item["password_hash"] = owner.password_hash.value
        item["public_key"] = owner.public_key.value
        item["created_at"] = owner.created_at.value
        item["salt"] = owner.salt
        item["random_entropy"] = owner.random_entropy
        item["owner_encrypted_storage"] = owner.owner_encrypted_storage
        item["state"] = owner.state.value if hasattr(owner.state, "value") else owner.state
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(owner_hash)")
        except ClientError as e:
            logger.error(f"create_owner client error: {e}")
            raise

    def get_owner(self, owner_hash: str) -> Optional[Owner]:
        """
        Read all fields of an owner; returns validated Owner or None if not found.

        Args:
            owner_hash (str): Owner hash key.
        Returns:
            Optional[Owner]: Owner object if found and valid, else None.
        Raises:
            ClientError: If DynamoDB get_item fails.
            ValidationError: If the item cannot be validated as an Owner.
            Exception: For unknown errors (re-raised).
        """
        try:
            response = self.table.get_item(Key={"owner_hash": owner_hash if isinstance(owner_hash, str) else owner_hash.value})
            item = response.get("Item")
            if item:
                item = dynamodb_decimal_to_int(item)
                if "owner_hash" in item:
                    item["owner_hash"] = OwnerHash(value=item["owner_hash"])
                if "password_hash" in item:
                    item["password_hash"] = PasswordHash(value=item["password_hash"])
                if "public_key" in item:
                    item["public_key"] = PublicKey(value=item["public_key"])
                if "created_at" in item:
                    item["created_at"] = Timestamp(value=item["created_at"])
            return Owner.model_validate(item) if item else None
        except ClientError as e:
            logger.error(f"get_owner client error: {e}")
            raise
        except ValidationError as e:
            logger.error(f"get_owner validation error: {e}")
            return None
        except Exception as e:
            logger.error(f"get_owner unknown error: {e}")
            raise

    def get_owner_field(self, owner_hash: str, field: str) -> Optional[Any]:
        """
        Read a single field of an owner document.

        Args:
            owner_hash (str): Owner hash key.
            field (str): Field name to retrieve.
        Returns:
            Optional[Any]: Value of the field if present, else None.
        Raises:
            ClientError: If DynamoDB get_item fails.
            Exception: For unknown errors (re-raised).
        """
        try:
            expr_names = {f"#{field}": field}
            response = self.table.get_item(Key={"owner_hash": owner_hash}, ProjectionExpression=f"#{field}", ExpressionAttributeNames=expr_names)
            item = response.get("Item")
            if item and field in item:
                return item[field]
            return None
        except ClientError as e:
            logger.error(f"get_owner_field client error: {e}")
            raise
        except Exception as e:  #pylint: disable=broad-except
            logger.error(f"get_owner_field unknown error: {e}")
            raise

    def put_owner(self, owner: Owner) -> None:
        """
        Create or overwrite the entire owner record.

        Args:
            owner (Owner): Owner object to write.
        Raises:
            Exception: If DynamoDB put_item fails (re-raised).
        """
        try:
            item = owner.model_dump()
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

    def update_owner_field(self, owner_hash: str, field: str, value: Any) -> Dict[str, Any]:
        """
        Update a single field for an existing owner.

        Args:
            owner_hash (str): Owner hash key.
            field (str): Field name to update.
            value (Any): New value for the field.
        Returns:
            Dict[str, Any]: Response from DynamoDB update_item.
        Raises:
            ValueError: If field is not allowed to be updated.
            Exception: If DynamoDB update_item fails (re-raised).
        """
        if field not in Owner.ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"field >{field}< not part of Owner")
        key_value = owner_hash
        resp = self.table.update_item(
            Key={"owner_hash": key_value},
            UpdateExpression="SET #field = :val",
            ExpressionAttributeNames={"#field": field},
            ExpressionAttributeValues={":val": value},
        )
        return resp

    def update_owner_fields(self, owner_hash: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update multiple fields for an existing owner.

        Args:
            owner_hash (str): Owner hash key.
            updates (Dict[str, Any]): Dictionary of field updates.
        Returns:
            Optional[Dict[str, Any]]: Updated attributes from DynamoDB, if any.
        Raises:
            ValueError: If any field is not allowed to be updated.
            Exception: If DynamoDB update_item fails (re-raised).
        """
        not_allowed = [k for k in updates if k not in Owner.ALLOWED_UPDATE_FIELDS]
        if not_allowed:
            raise ValueError(f"Not allowed to update fields: {not_allowed}")
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

    def delete_owner(self, owner_hash: str) -> None:
        """
        Delete the owner record from the database.

        Args:
            owner_hash (str): Owner hash key.
        Raises:
            ClientError: If DynamoDB delete_item fails.
        """
        try:
            self.table.delete_item(Key={"owner_hash": owner_hash})
        except ClientError as e:
            logger.error(f"delete_owner error: {e}")
            raise
