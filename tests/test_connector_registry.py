"""Unit tests for connector registry ordering, factory, and validation."""

import pytest

from data_profiling.connectors import (
    ConnectorConfigError,
    FileConnector,
    MongoDBConnector,
    REGISTRY,
    SQLConnector,
    SnowflakeConnector,
    create_connector,
)


EXPECTED_GROUPS = ["file", "databases", "cloud_warehouses"]
EXPECTED_CONNECTORS = {
    "file": ["csv", "json"],
    "databases": ["postgres", "mysql", "mariadb", "sqlserver", "oracle", "mongodb"],
    "cloud_warehouses": ["gcp_bigquery", "aws_redshift", "azure_synapse", "snowflake"],
}


def test_registry_group_ordering() -> None:
    """Validate that top-level groups keep the required deterministic order."""
    groups = REGISTRY.list_groups()
    assert [group.id for group in groups] == EXPECTED_GROUPS


def test_registry_connector_ordering_inside_groups() -> None:
    """Validate connector ordering inside each group."""
    for group_id, expected_ids in EXPECTED_CONNECTORS.items():
        connectors = REGISTRY.list_connectors(group_id=group_id)
        assert [connector.id for connector in connectors] == expected_ids


def test_ui_metadata_matches_expected_order() -> None:
    """Validate grouped UI metadata order and cloud provider display labels."""
    ui_metadata = REGISTRY.grouped_ui_options()
    assert [group["id"] for group in ui_metadata] == EXPECTED_GROUPS
    assert [c["id"] for c in ui_metadata[0]["connectors"]] == EXPECTED_CONNECTORS["file"]
    warehouse_labels = [c["label"] for c in ui_metadata[2]["connectors"]]
    assert warehouse_labels == ["GCP BigQuery", "AWS Redshift", "Azure Synapse", "Snowflake"]


def test_factory_returns_expected_classes() -> None:
    """Validate factory class resolution for representative connector IDs."""
    assert isinstance(
        create_connector("csv", {"type": "file", "format": "csv", "path": "x.csv"}),
        FileConnector,
    )
    assert isinstance(
        create_connector(
            "postgres",
            {
                "type": "sql",
                "driver": "postgresql",
                "connection_string": "postgresql+psycopg2://user:pass@host/db",
            },
        ),
        SQLConnector,
    )
    assert isinstance(
        create_connector(
            "mongodb",
            {
                "type": "nosql",
                "driver": "mongodb",
                "connection_string": "mongodb://localhost:27017",
            },
        ),
        MongoDBConnector,
    )
    assert isinstance(
        create_connector(
            "snowflake",
            {
                "type": "warehouse",
                "provider": "snowflake",
                "service": "snowflake",
                "connection_string": "snowflake://user:pass@account/db/schema?warehouse=wh",
            },
        ),
        SnowflakeConnector,
    )


@pytest.mark.parametrize(
    "connector_id,config",
    [
        ("csv", {"type": "file", "format": "csv"}),
        (
            "postgres",
            {
                "type": "sql",
                "driver": "postgresql",
            },
        ),
        (
            "gcp_bigquery",
            {
                "type": "warehouse",
                "provider": "gcp",
                "service": "bigquery",
            },
        ),
    ],
)
def test_required_field_validation(connector_id: str, config: dict) -> None:
    """Validate required field enforcement across connector families."""
    with pytest.raises(ConnectorConfigError):
        create_connector(connector_id, config)


def test_snowflake_requires_connection_string_or_explicit_fields() -> None:
    """Validate Snowflake requires URI or minimum explicit credential set."""
    with pytest.raises(ConnectorConfigError):
        create_connector(
            "snowflake",
            {
                "type": "warehouse",
                "provider": "snowflake",
                "service": "snowflake",
            },
        )
