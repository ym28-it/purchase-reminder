"""DynamoDB Local fixtures for integration and environment tests."""

from collections.abc import Iterator

import pytest

from scripts.dynamodb_test_environment import (
    DynamoDBTestEnvironment,
    clear_dynamodb_caches,
    delete_test_table,
    get_test_dynamodb_resource,
    recreate_test_table,
    validate_test_environment,
)


@pytest.fixture(scope="session", autouse=True)
def dynamodb_test_session() -> Iterator[DynamoDBTestEnvironment]:
    """Require the approved runner and bind this pytest session to its table."""
    try:
        environment = validate_test_environment()
        clear_dynamodb_caches()
        dynamodb = get_test_dynamodb_resource()
        dynamodb.meta.client.list_tables(Limit=1)
    except Exception as error:
        pytest.exit(f"ENVIRONMENT_FAILURE: integration setup failed: {error}", returncode=70)
    try:
        yield environment
    finally:
        clear_dynamodb_caches()


@pytest.fixture(autouse=True)
def empty_dynamodb_table(dynamodb_test_session: DynamoDBTestEnvironment) -> Iterator[None]:
    """Start every test from a newly created, empty MAIN_TABLE_SCHEMA table."""
    try:
        clear_dynamodb_caches()
        dynamodb = get_test_dynamodb_resource()
        recreate_test_table(dynamodb, dynamodb_test_session.table_name)
    except Exception as error:
        pytest.exit(f"ENVIRONMENT_FAILURE: table setup failed: {error}", returncode=70)
    try:
        yield
    finally:
        try:
            clear_dynamodb_caches()
            dynamodb = get_test_dynamodb_resource()
            delete_test_table(dynamodb, dynamodb_test_session.table_name)
            clear_dynamodb_caches()
        except Exception as error:
            pytest.exit(f"ENVIRONMENT_FAILURE: table cleanup failed: {error}", returncode=70)
