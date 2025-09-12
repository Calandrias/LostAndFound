import os
import boto3
from typing import Optional, Any, Dict
from botocore.exceptions import ClientError
from .owner_model import Owner


class OwnerStore:

    def __init__(self, table_name: Optional[str] = None, ddb_resource: Optional[Any] = None):
        """
        Owner DB client for accessing Owner records in DynamoDB.
        :param table_name: DynamoDB table name for owners.
        :param ddb_resource: boto3 resource (for mocking/testing).
        """
        self.table_name = table_name or os.environ.get("OWNER_TABLE_NAME", "LostAndFound-Owner")
        self.ddb = ddb_resource or boto3.resource("dynamodb")
        self.table = self.ddb.Table(self.table_name)

    def get_owner(self, owner_hash: str) -> Optional[Owner]:
        """Read all fields of an owner; returns validated Owner or None if not found."""
        try:
            response = self.table.get_item(Key={"owner_hash": owner_hash})
            item = response.get("Item")
            return Owner.model_validate(item) if item else None
        except Exception as e:
            print(f"get_owner error: {e}")
            return None

    def get_owner_field(self, owner_hash: str, field: str) -> Optional[Any]:
        """Read a single field of an owner document."""
        try:
            response = self.table.get_item(Key={"owner_hash": owner_hash}, ProjectionExpression=field)
            item = response.get("Item")
            return item.get(field) if item else None
        except Exception as e:
            print(f"get_owner_field error: {e}")
            return None

    def put_owner(self, owner: Owner):
        """Create or overwrite the entire owner record."""
        item = owner.model_dump(mode="json", exclude_unset=True)
        try:
            self.table.put_item(Item=item)
        except ClientError as e:
            print(f"put_owner error: {e}")
            raise

    def update_owner_field(self, owner_hash: str, field: str, value: Any):
        """Update a single field for an existing owner."""
        try:
            expr_names = {f"#{field}": field}
            resp = self.table.update_item(Key={"owner_hash": owner_hash},
                                          UpdateExpression=f"SET #{field} = :v",
                                          ExpressionAttributeValues={":v": value},
                                          ExpressionAttributeNames=expr_names,
                                          ReturnValues="UPDATED_NEW")
            return resp.get("Attributes", {}).get(field)
        except Exception as e:
            print(f"update_owner_field error: {e}")
            raise

    def update_owner_fields(self, owner_hash: str, updates: Dict[str, Any]):
        """Update multiple fields for an existing owner."""
        expr = "SET " + ", ".join(f"{k}=:{k}" for k in updates)
        attrs = {f":{k}": v for k, v in updates.items()}
        try:
            resp = self.table.update_item(Key={"owner_hash": owner_hash}, UpdateExpression=expr, ExpressionAttributeValues=attrs, ReturnValues="UPDATED_NEW")
            return resp.get("Attributes")
        except Exception as e:
            print(f"update_owner_fields error: {e}")
            raise

    def delete_owner(self, owner_hash: str):
        """Delete the owner record from the database."""
        try:
            self.table.delete_item(Key={"owner_hash": owner_hash})
        except ClientError as e:
            print(f"delete_owner error: {e}")
            raise
