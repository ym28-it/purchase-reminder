from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import run_with_dynamodb_local as runner


def test_maven_truststore_is_not_created_without_extra_ca(tmp_path: Path) -> None:
    assert runner._write_maven_truststore(tmp_path, {}) is None


def test_maven_truststore_imports_configured_ca(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    java_home = tmp_path / "java"
    keytool = java_home / "bin" / "keytool"
    cacerts = java_home / "lib" / "security" / "cacerts"
    certificate = tmp_path / "environment-ca.crt"
    keytool.parent.mkdir(parents=True)
    cacerts.parent.mkdir(parents=True)
    keytool.write_text("keytool")
    cacerts.write_text("default truststore")
    certificate.write_text("certificate")
    captured_command: list[str] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        captured_command.extend(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    truststore = runner._write_maven_truststore(
        tmp_path / "cache",
        {
            "JAVA_HOME": str(java_home),
            "NODE_EXTRA_CA_CERTS": str(certificate),
        },
    )

    assert truststore is not None
    assert truststore.read_text() == "default truststore"
    assert captured_command[0] == str(keytool)
    assert captured_command[captured_command.index("-file") + 1] == str(certificate)
    assert captured_command[captured_command.index("-keystore") + 1] == str(truststore)


def test_maven_truststore_rejects_missing_configured_ca(tmp_path: Path) -> None:
    with pytest.raises(runner.EnvironmentSetupError, match="not readable"):
        runner._write_maven_truststore(
            tmp_path / "cache",
            {
                "JAVA_HOME": str(tmp_path / "java"),
                "SSL_CERT_FILE": str(tmp_path / "missing.crt"),
            },
        )
