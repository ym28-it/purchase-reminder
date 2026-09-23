"""Environment-only smoke and fail-closed tests for DynamoDB Local."""

from pathlib import Path

import pytest

from app.core import dynamodb as dynamodb_module
from app.core.config import get_settings
from app.core.dynamodb import get_dynamodb_resource, get_table
from scripts import run_with_dynamodb_local as runner
from scripts.dynamodb_test_environment import (
    DynamoDBTestEnvironment,
    EnvironmentContractError,
    clear_dynamodb_caches,
    get_test_dynamodb_resource,
    recreate_test_table,
    validate_test_environment,
)

pytestmark = pytest.mark.integration


def test_local_api_and_test_table_are_ready(
    dynamodb_test_session: DynamoDBTestEnvironment,
) -> None:
    dynamodb = get_test_dynamodb_resource()

    tables = dynamodb.meta.client.list_tables()["TableNames"]
    description = dynamodb.meta.client.describe_table(TableName=dynamodb_test_session.table_name)

    assert dynamodb_test_session.table_name in tables
    assert description["Table"]["TableName"] == dynamodb_test_session.table_name
    assert description["Table"]["TableStatus"] == "ACTIVE"


def test_generic_item_can_be_written_and_read(
    dynamodb_test_session: DynamoDBTestEnvironment,
) -> None:
    table = get_test_dynamodb_resource().Table(dynamodb_test_session.table_name)
    item = {
        "PK": "ENVIRONMENT#SMOKE",
        "SK": "ITEM#1",
        "value": "verified",
    }

    table.put_item(Item=item)
    response = table.get_item(Key={"PK": item["PK"], "SK": item["SK"]})

    assert response["Item"] == item


def test_each_test_starts_with_an_empty_table(
    dynamodb_test_session: DynamoDBTestEnvironment,
) -> None:
    table = get_test_dynamodb_resource().Table(dynamodb_test_session.table_name)

    assert table.scan(Select="COUNT")["Count"] == 0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DYNAMODB_ENDPOINT_URL", None),
        ("DYNAMODB_ENDPOINT_URL", "http://dynamodb.ap-northeast-1.amazonaws.com:8001"),
        ("DYNAMODB_ENDPOINT_URL", "http://127.0.0.1:9999"),
        ("AWS_ACCESS_KEY_ID", "not-dummy"),
        ("AWS_PROFILE", "real-profile"),
        ("AWS_SESSION_TOKEN", "real-session-token"),
    ],
)
def test_invalid_environment_fails_before_sdk_access(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str | None,
) -> None:
    sdk_accessed = False

    def unexpected_sdk_access(*args: object, **kwargs: object) -> None:
        nonlocal sdk_accessed
        sdk_accessed = True
        raise AssertionError("boto3.resource must not be called")

    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(dynamodb_module.boto3, "resource", unexpected_sdk_access)
    clear_dynamodb_caches()

    with pytest.raises(EnvironmentContractError):
        get_test_dynamodb_resource()

    assert sdk_accessed is False
    clear_dynamodb_caches()


def test_checksum_mismatch_stops_before_extraction_or_jar_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version_root = tmp_path / "3.3.1"
    version_root.mkdir()
    (version_root / "dynamodb_local.tar.gz").write_bytes(b"corrupt")
    extraction_attempted = False
    jar_execution_attempted = False

    def unexpected_extraction(*args: object, **kwargs: object) -> None:
        nonlocal extraction_attempted
        extraction_attempted = True

    def unexpected_jar_execution(*args: object, **kwargs: object) -> str:
        nonlocal jar_execution_attempted
        jar_execution_attempted = True
        return "3.3.1"

    monkeypatch.setattr(runner, "_extract_archive", unexpected_extraction)
    monkeypatch.setattr(runner, "_read_dynamodb_version", unexpected_jar_execution)
    lock = runner.DynamoDBLocalLock("3.3.1", "https://example.invalid", "0" * 64)

    with pytest.raises(runner.EnvironmentSetupError, match="checksum mismatch"):
        runner._prepare_distribution(lock, tmp_path, "java")

    assert extraction_attempted is False
    assert jar_execution_attempted is False


def test_java_process_start_oserror_returns_environment_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock = runner.DynamoDBLocalLock("3.3.1", "https://example.invalid", "0" * 64)
    arguments = runner.argparse.Namespace(port=18001, command=["true"])
    monkeypatch.setattr(runner, "_parse_arguments", lambda: arguments)
    monkeypatch.setattr(runner.shutil, "which", lambda executable: "/usr/bin/java")
    monkeypatch.setattr(runner, "_run_java_version", lambda java: "openjdk version 17")
    monkeypatch.setattr(runner, "_load_lock", lambda path: lock)
    monkeypatch.setattr(
        runner,
        "_prepare_distribution",
        lambda lock, cache_root, java: (tmp_path / "DynamoDBLocal.jar", tmp_path / "lib"),
    )
    monkeypatch.setattr(runner, "_assert_port_available", lambda port: None)

    def fail_to_start(*args: object, **kwargs: object) -> None:
        raise OSError("java process start denied")

    monkeypatch.setattr(runner.subprocess, "Popen", fail_to_start)

    assert runner.main() == runner.ENVIRONMENT_FAILURE_EXIT
    assert "ENVIRONMENT_FAILURE: java process start denied" in capsys.readouterr().err


def test_cache_clear_removes_all_cached_aws_objects(
    dynamodb_test_session: DynamoDBTestEnvironment,
) -> None:
    get_settings()
    get_dynamodb_resource()
    get_table(dynamodb_test_session.table_name)

    clear_dynamodb_caches()

    assert get_settings.cache_info().currsize == 0
    assert get_dynamodb_resource.cache_info().currsize == 0
    assert get_table.cache_info().currsize == 0


def test_recreate_removes_previous_test_data(
    dynamodb_test_session: DynamoDBTestEnvironment,
) -> None:
    dynamodb = get_test_dynamodb_resource()
    table = dynamodb.Table(dynamodb_test_session.table_name)
    table.put_item(Item={"PK": "OLD", "SK": "OLD"})

    recreated = recreate_test_table(dynamodb, dynamodb_test_session.table_name)

    assert recreated.scan(Select="COUNT")["Count"] == 0


def test_environment_contract_is_valid(dynamodb_test_session: DynamoDBTestEnvironment) -> None:
    assert validate_test_environment() == dynamodb_test_session
