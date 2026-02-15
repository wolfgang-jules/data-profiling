from __future__ import annotations

from pathlib import Path

from data_profiling.connectors import create_connector


class _FakeConnection:
    def close(self) -> None:
        return None


class _FakeEngine:
    def connect(self) -> _FakeConnection:
        return _FakeConnection()


class _FakeMongoAdmin:
    def command(self, command_name: str) -> dict:
        assert command_name == "ping"
        return {"ok": 1}


class _FakeMongoClient:
    def __init__(self, *args, **kwargs) -> None:
        self.admin = _FakeMongoAdmin()

    def close(self) -> None:
        return None


class _FakeBigQueryClient:
    def __init__(self, *args, **kwargs) -> None:
        return None

    @classmethod
    def from_service_account_json(cls, credentials_path: str, project: str):
        return cls(credentials_path, project)

    def list_datasets(self, max_results: int = 1):
        return ["dataset"]


class _FakeBigQueryModule:
    Client = _FakeBigQueryClient


def test_file_connector_test_connection_true(tmp_path: Path) -> None:
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("a,b\n1,2", encoding="utf-8")

    connector = create_connector(
        "csv",
        {
            "type": "file",
            "format": "csv",
            "path": str(csv_file),
        },
    )

    assert connector.test_connection() is True


def test_file_connector_test_connection_false(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.csv"

    connector = create_connector(
        "csv",
        {
            "type": "file",
            "format": "csv",
            "path": str(missing_file),
        },
    )

    assert connector.test_connection() is False


def test_sql_connector_test_connection(monkeypatch) -> None:
    def fake_import_sqlalchemy():
        def fake_create_engine(*args, **kwargs):
            return _FakeEngine()

        return fake_create_engine

    monkeypatch.setattr(
        "data_profiling.connectors.SQLConnector._import_sqlalchemy", staticmethod(fake_import_sqlalchemy)
    )

    connector = create_connector(
        "postgres",
        {
            "type": "sql",
            "driver": "postgresql",
            "connection_string": "postgresql+psycopg2://user:pass@localhost:5432/test",
        },
    )

    assert connector.test_connection() is True


def test_mongodb_connector_test_connection(monkeypatch) -> None:
    monkeypatch.setattr(
        "data_profiling.connectors.MongoDBConnector._import_pymongo", staticmethod(lambda: _FakeMongoClient)
    )

    connector = create_connector(
        "mongodb",
        {
            "type": "nosql",
            "driver": "mongodb",
            "connection_string": "mongodb://localhost:27017",
        },
    )

    assert connector.test_connection() is True


def test_bigquery_connector_test_connection(monkeypatch) -> None:
    monkeypatch.setattr(
        "data_profiling.connectors.BigQueryConnector._import_bigquery",
        staticmethod(lambda: _FakeBigQueryModule),
    )

    connector = create_connector(
        "gcp-bigquery",
        {
            "type": "warehouse",
            "provider": "gcp",
            "service": "bigquery",
            "project_id": "my-project",
        },
    )

    assert connector.test_connection() is True


def test_snowflake_connector_test_connection_with_explicit_fields(monkeypatch) -> None:
    def fake_import_sqlalchemy():
        def fake_create_engine(*args, **kwargs):
            return _FakeEngine()

        return fake_create_engine

    monkeypatch.setattr(
        "data_profiling.connectors.SQLConnector._import_sqlalchemy", staticmethod(fake_import_sqlalchemy)
    )

    connector = create_connector(
        "snowflake",
        {
            "type": "warehouse",
            "provider": "snowflake",
            "service": "snowflake",
            "account": "acme-org",
            "user": "analyst",
            "password": "secret",
            "warehouse": "compute_wh",
            "database": "analytics",
            "schema": "public",
        },
    )

    assert connector.test_connection() is True
