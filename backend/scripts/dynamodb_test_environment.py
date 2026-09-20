"""Shared fail-closed helpers for the DynamoDB Local test environment."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.dynamodb import get_dynamodb_resource, get_table
from app.models.table import MAIN_TABLE_SCHEMA

DEFAULT_LOCAL_PORT = 8001
TEST_TABLE_PREFIX = "purchase-reminder-test-"
DUMMY_CREDENTIAL = "dummy"
DISALLOWED_AWS_VARIABLES = (
    "AWS_PROFILE",
    "AWS_SESSION_TOKEN",
    "AWS_ROLE_ARN",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
)


class EnvironmentContractError(RuntimeError):
    """Raised before SDK access when the local-test safety contract is invalid."""


@dataclass(frozen=True)
class DynamoDBTestEnvironment:
    endpoint_url: str
    table_name: str
    region: str
    port: int


def validate_test_environment(
    environ: Mapping[str, str] | None = None,
) -> DynamoDBTestEnvironment:
    """Validate every local-only invariant before a boto3 resource is created."""
    values = os.environ if environ is None else environ
    endpoint_url = values.get("DYNAMODB_ENDPOINT_URL")
    if not endpoint_url:
        raise EnvironmentContractError("DYNAMODB_ENDPOINT_URL is required")

    parsed = urlparse(endpoint_url)
    if parsed.scheme != "http":
        raise EnvironmentContractError("DYNAMODB_ENDPOINT_URL must use http")
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise EnvironmentContractError("DYNAMODB_ENDPOINT_URL must use a loopback host")
    if parsed.username or parsed.password or parsed.path not in {"", "/"}:
        raise EnvironmentContractError(
            "DYNAMODB_ENDPOINT_URL must not contain credentials or a path"
        )
    if parsed.query or parsed.fragment:
        raise EnvironmentContractError("DYNAMODB_ENDPOINT_URL must not contain query or fragment")

    try:
        endpoint_port = parsed.port
        expected_port = int(values.get("DYNAMODB_LOCAL_PORT", str(DEFAULT_LOCAL_PORT)))
    except ValueError as error:
        raise EnvironmentContractError("DynamoDB Local port must be an integer") from error
    if endpoint_port is None or endpoint_port != expected_port:
        raise EnvironmentContractError(
            f"DYNAMODB_ENDPOINT_URL port must match DYNAMODB_LOCAL_PORT ({expected_port})"
        )

    table_name = values.get("DYNAMODB_TABLE_NAME", "")
    if not table_name.startswith(TEST_TABLE_PREFIX) or table_name == TEST_TABLE_PREFIX:
        raise EnvironmentContractError(
            f"DYNAMODB_TABLE_NAME must start with {TEST_TABLE_PREFIX!r} and include a session id"
        )

    if values.get("AWS_ACCESS_KEY_ID") != DUMMY_CREDENTIAL:
        raise EnvironmentContractError("AWS_ACCESS_KEY_ID must be the dummy value")
    if values.get("AWS_SECRET_ACCESS_KEY") != DUMMY_CREDENTIAL:
        raise EnvironmentContractError("AWS_SECRET_ACCESS_KEY must be the dummy value")

    region = values.get("AWS_DEFAULT_REGION", "")
    if region != "ap-northeast-1":
        raise EnvironmentContractError("AWS_DEFAULT_REGION must be ap-northeast-1")
    if values.get("AWS_EC2_METADATA_DISABLED", "").lower() != "true":
        raise EnvironmentContractError("AWS_EC2_METADATA_DISABLED must be true")

    inherited = [name for name in DISALLOWED_AWS_VARIABLES if values.get(name)]
    if inherited:
        raise EnvironmentContractError(
            f"real-AWS credential settings are not allowed: {', '.join(inherited)}"
        )

    return DynamoDBTestEnvironment(endpoint_url, table_name, region, endpoint_port)


def clear_dynamodb_caches() -> None:
    """Clear all cached settings and boto3 objects at an environment boundary."""
    get_table.cache_clear()
    get_dynamodb_resource.cache_clear()
    get_settings.cache_clear()


def get_test_dynamodb_resource() -> Any:
    """Return the configured resource only after the fail-closed guard passes."""
    validate_test_environment()
    return get_dynamodb_resource()


def _validate_resource_endpoint(dynamodb: Any, expected_endpoint: str) -> None:
    actual_endpoint = dynamodb.meta.client.meta.endpoint_url.rstrip("/")
    if actual_endpoint != expected_endpoint.rstrip("/"):
        raise EnvironmentContractError(
            "DynamoDB resource endpoint mismatch: "
            f"expected {expected_endpoint}, got {actual_endpoint}"
        )


def delete_test_table(dynamodb: Any, table_name: str) -> None:
    """Delete the guarded test table if it exists; safe to call repeatedly."""
    environment = validate_test_environment()
    if table_name != environment.table_name:
        raise EnvironmentContractError("refusing to delete a table outside this test session")
    _validate_resource_endpoint(dynamodb, environment.endpoint_url)

    client = dynamodb.meta.client
    try:
        client.describe_table(TableName=table_name)
    except client.exceptions.ResourceNotFoundException:
        return
    table = dynamodb.Table(table_name)
    table.delete()
    table.wait_until_not_exists()


def recreate_test_table(dynamodb: Any, table_name: str) -> Any:
    """Recreate the guarded test table from MAIN_TABLE_SCHEMA and verify it."""
    environment = validate_test_environment()
    if table_name != environment.table_name:
        raise EnvironmentContractError("refusing to recreate a table outside this test session")
    _validate_resource_endpoint(dynamodb, environment.endpoint_url)

    delete_test_table(dynamodb, table_name)
    table = dynamodb.create_table(**MAIN_TABLE_SCHEMA.to_create_table_kwargs(table_name))
    table.wait_until_exists()
    description = dynamodb.meta.client.describe_table(TableName=table_name)
    if description["Table"]["TableName"] != table_name:
        raise EnvironmentContractError("DescribeTable returned an unexpected table")
    return table
