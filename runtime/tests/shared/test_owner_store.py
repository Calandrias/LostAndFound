import pytest
from moto import mock_aws
import boto3

from runtime.shared.owner.owner_model import Owner
from runtime.shared.owner.owner_strore import OwnerStore


@pytest.fixture
def ddb_table():
    with mock_aws():
        # DynamoDB-Resource und Tabelle anlegen (Schema muss passen!)
        dynamodb = boto3.resource("dynamodb", region_name="eu-central-1")
        table = dynamodb.create_table(TableName="LostAndFound-Owner",
                                      KeySchema=[{
                                          "AttributeName": "owner_hash",
                                          "KeyType": "HASH"
                                      }],
                                      AttributeDefinitions=[{
                                          "AttributeName": "owner_hash",
                                          "AttributeType": "S"
                                      }],
                                      ProvisionedThroughput={
                                          "ReadCapacityUnits": 5,
                                          "WriteCapacityUnits": 5
                                      })
        table.wait_until_exists()  # Manche moto-Backends brauchen das!
        yield dynamodb


def make_owner():
    # Gültige Testdaten mit minimalen Anforderungen
    return Owner(owner_hash="A" * 43,
                 salt="B" * 22,
                 password_hash="$2a$12$" + "C" * 53,
                 public_key="-----BEGIN PUBLIC KEY-----\n" + "X" * 272 + "\n-----END PUBLIC KEY-----\n",
                 random_entropy="F" * 32,
                 created_at=1672531200,
                 status="active")


def test_put_and_get_owner(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    loaded = store.get_owner(owner.owner_hash)
    assert loaded is not None
    assert loaded.owner_hash == owner.owner_hash


def test_update_owner_field(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    updated = store.update_owner_field(owner.owner_hash, "status", "blocked")
    assert updated == "blocked"
    loaded = store.get_owner(owner.owner_hash)
    assert loaded.status == "blocked"
