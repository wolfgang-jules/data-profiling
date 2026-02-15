"""Core connector abstractions, registry, and factory for data sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class ConnectorConfigError(ValueError):
    """Raised when connector configuration is invalid."""


class ConnectorDependencyError(ImportError):
    """Raised when an optional dependency required by a connector is missing."""


class ConnectorRuntimeError(RuntimeError):
    """Raised when connector operations fail at runtime."""


@dataclass(frozen=True)
class ConnectorSpec:
    """Metadata and validation contract for a connector type."""

    id: str
    group: str
    label: str
    order: int
    type: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...] = ()
    help_text: str = ""
    driver: Optional[str] = None
    provider: Optional[str] = None
    service: Optional[str] = None


@dataclass(frozen=True)
class ConnectorGroup:
    """Metadata for UI grouping and ordering."""

    id: str
    label: str
    order: int


class BaseConnector:
    """Common connector interface."""

    def __init__(self, connector_id: str, config: Dict[str, Any], spec: ConnectorSpec) -> None:
        self.connector_id = connector_id
        self.config = config
        self.spec = spec
        self.validate()

    def validate(self) -> None:
        missing = [field for field in self.spec.required_fields if not self.config.get(field)]
        if missing:
            raise ConnectorConfigError(
                f"Connector '{self.connector_id}' missing required fields: {', '.join(missing)}"
            )
        if self.spec.type and self.config.get("type") != self.spec.type:
            raise ConnectorConfigError(
                f"Connector '{self.connector_id}' requires type='{self.spec.type}'."
            )
        if self.spec.driver and self.config.get("driver") != self.spec.driver:
            raise ConnectorConfigError(
                f"Connector '{self.connector_id}' requires driver='{self.spec.driver}'."
            )
        if self.spec.provider and self.config.get("provider") != self.spec.provider:
            raise ConnectorConfigError(
                f"Connector '{self.connector_id}' requires provider='{self.spec.provider}'."
            )
        if self.spec.service and self.config.get("service") != self.spec.service:
            raise ConnectorConfigError(
                f"Connector '{self.connector_id}' requires service='{self.spec.service}'."
            )

    def connect(self) -> Any:
        raise NotImplementedError

    def read(self, query_or_path: str, **kwargs: Any) -> Any:
        raise NotImplementedError

    def test_connection(self) -> bool:
        raise NotImplementedError


class FileConnector(BaseConnector):
    """Connector for file-based sources (CSV/JSON)."""

    def validate(self) -> None:
        super().validate()
        expected_format = self.connector_id
        if self.config.get("format") != expected_format:
            raise ConnectorConfigError(
                f"Connector '{self.connector_id}' requires format='{expected_format}'."
            )

    def connect(self) -> Path:
        path = Path(self.config["path"]).expanduser().resolve()
        return path

    def read(self, query_or_path: str, **kwargs: Any) -> Any:
        import pandas as pd

        effective_path = query_or_path or self.config["path"]
        options = dict(self.config.get("options", {}))
        options.update(kwargs)
        path = Path(effective_path)
        file_format = self.config.get("format")

        if file_format == "csv":
            return pd.read_csv(path, **options)
        if file_format == "json":
            return pd.read_json(path, **options)
        raise ConnectorRuntimeError(
            f"Unsupported file format '{file_format}' for connector '{self.connector_id}'."
        )

    def test_connection(self) -> bool:
        return self.connect().exists()


class SQLConnector(BaseConnector):
    """Connector for SQL-based engines using SQLAlchemy connection strings."""

    def validate(self) -> None:
        super().validate()

    @staticmethod
    def _import_sqlalchemy() -> Any:
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:
            raise ConnectorDependencyError(
                "Missing dependency 'sqlalchemy'. Install connector extras, for example: "
                "pip install .[postgres]"
            ) from exc
        return create_engine

    def connect(self) -> Any:
        create_engine = self._import_sqlalchemy()
        options = dict(self.config.get("options", {}))
        try:
            return create_engine(self.config["connection_string"], **options)
        except Exception as exc:  # pragma: no cover - driver-specific runtime path
            raise ConnectorRuntimeError(
                f"Failed to create SQL engine for connector '{self.connector_id}': {exc}"
            ) from exc

    def read(self, query_or_path: str, **kwargs: Any) -> Any:
        import pandas as pd

        if not query_or_path:
            raise ConnectorConfigError(
                f"Connector '{self.connector_id}' requires a SQL query in read(query_or_path=...)."
            )
        engine = self.connect()
        return pd.read_sql(query_or_path, con=engine, **kwargs)

    def test_connection(self) -> bool:
        engine = self.connect()
        connection = None
        try:
            connection = engine.connect()
            return True
        except Exception as exc:
            raise ConnectorRuntimeError(
                f"Connection test failed for connector '{self.connector_id}': {exc}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()


class MongoDBConnector(BaseConnector):
    """Connector for MongoDB."""

    def validate(self) -> None:
        super().validate()

    @staticmethod
    def _import_pymongo() -> Any:
        try:
            from pymongo import MongoClient
        except ImportError as exc:
            raise ConnectorDependencyError(
                "Missing dependency 'pymongo'. Install with: pip install .[mongodb]"
            ) from exc
        return MongoClient

    def connect(self) -> Any:
        client_cls = self._import_pymongo()
        options = dict(self.config.get("options", {}))
        return client_cls(self.config["connection_string"], **options)

    def read(self, query_or_path: str, **kwargs: Any) -> Any:
        if not query_or_path:
            raise ConnectorConfigError(
                "MongoDB read() expects query_or_path as 'database.collection'."
            )

        database_name, collection_name = _split_database_collection(query_or_path)
        client = self.connect()
        options = kwargs or {}
        filter_query = options.get("filter", {})
        projection = options.get("projection")
        limit = options.get("limit")

        cursor = client[database_name][collection_name].find(filter_query, projection)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def test_connection(self) -> bool:
        client = self.connect()
        try:
            client.admin.command("ping")
            return True
        except Exception as exc:
            raise ConnectorRuntimeError(
                f"Connection test failed for connector '{self.connector_id}': {exc}"
            ) from exc
        finally:
            client.close()


class BigQueryConnector(BaseConnector):
    """Connector for Google BigQuery."""

    def validate(self) -> None:
        super().validate()

    @staticmethod
    def _import_bigquery() -> Any:
        try:
            from google.cloud import bigquery
        except ImportError as exc:
            raise ConnectorDependencyError(
                "Missing dependency 'google-cloud-bigquery'. Install with: pip install .[bigquery]"
            ) from exc
        return bigquery

    def connect(self) -> Any:
        bigquery = self._import_bigquery()
        credentials_path = self.config.get("credentials_path")
        project_id = self.config["project_id"]

        if credentials_path:
            return bigquery.Client.from_service_account_json(credentials_path, project=project_id)
        return bigquery.Client(project=project_id)

    def read(self, query_or_path: str, **kwargs: Any) -> Any:
        if not query_or_path:
            raise ConnectorConfigError("BigQuery read() requires a SQL query in query_or_path.")

        client = self.connect()
        options = dict(self.config.get("options", {}))
        options.update(kwargs)
        location = options.pop("location", None)
        query_job = client.query(query_or_path, location=location, **options)
        return query_job.result().to_dataframe()

    def test_connection(self) -> bool:
        client = self.connect()
        try:
            list(client.list_datasets(max_results=1))
            return True
        except Exception as exc:
            raise ConnectorRuntimeError(
                f"Connection test failed for connector '{self.connector_id}': {exc}"
            ) from exc


class SnowflakeConnector(SQLConnector):
    """Snowflake connector with either connection string or explicit parameters."""

    REQUIRED_EXPLICIT_FIELDS: tuple[str, ...] = (
        "account",
        "user",
        "password",
        "warehouse",
        "database",
        "schema",
    )

    def validate(self) -> None:
        super().validate()

        connection_string = self.config.get("connection_string")
        if connection_string:
            return

        missing = [f for f in self.REQUIRED_EXPLICIT_FIELDS if not self.config.get(f)]
        if missing:
            raise ConnectorConfigError(
                "Snowflake requires either 'connection_string' or explicit fields: "
                "account,user,password,warehouse,database,schema"
            )

    def connect(self) -> Any:
        if not self.config.get("connection_string"):
            self.config["connection_string"] = self._build_connection_string_from_fields()
        return super().connect()

    def _build_connection_string_from_fields(self) -> str:
        from urllib.parse import quote_plus

        user = quote_plus(str(self.config["user"]))
        password = quote_plus(str(self.config["password"]))
        account = self.config["account"]
        database = self.config["database"]
        schema = self.config["schema"]
        warehouse = quote_plus(str(self.config["warehouse"]))

        role_part = ""
        if self.config.get("role"):
            role_part = f"&role={quote_plus(str(self.config['role']))}"

        return (
            f"snowflake://{user}:{password}@{account}/{database}/{schema}"
            f"?warehouse={warehouse}{role_part}"
        )


def _split_database_collection(resource_name: str) -> tuple[str, str]:
    values = resource_name.split(".", 1)
    if len(values) != 2 or not values[0] or not values[1]:
        raise ConnectorConfigError(
            "MongoDB query_or_path must use format 'database.collection'."
        )
    return values[0], values[1]


class ConnectorRegistry:
    """Registry storing connector specs and groups with deterministic ordering."""

    def __init__(self) -> None:
        self._groups: list[ConnectorGroup] = [
            ConnectorGroup(id="file", label="file", order=1),
            ConnectorGroup(id="databases", label="databases (transactional)", order=2),
            ConnectorGroup(id="cloud_warehouses", label="cloud_warehouses", order=3),
        ]
        self._specs: list[ConnectorSpec] = [
            ConnectorSpec(
                id="csv",
                group="file",
                label="CSV",
                order=1,
                type="file",
                required_fields=("type", "format", "path"),
                optional_fields=("options",),
                help_text="Read data from a local or mounted CSV file.",
            ),
            ConnectorSpec(
                id="json",
                group="file",
                label="JSON",
                order=2,
                type="file",
                required_fields=("type", "format", "path"),
                optional_fields=("options",),
                help_text="Read data from a local or mounted JSON file.",
            ),
            ConnectorSpec(
                id="postgres",
                group="databases",
                label="Postgres",
                order=1,
                type="sql",
                driver="postgresql",
                required_fields=("type", "driver", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to PostgreSQL using a SQLAlchemy connection string.",
            ),
            ConnectorSpec(
                id="mysql",
                group="databases",
                label="MySQL",
                order=2,
                type="sql",
                driver="mysql",
                required_fields=("type", "driver", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to MySQL using a SQLAlchemy connection string.",
            ),
            ConnectorSpec(
                id="mariadb",
                group="databases",
                label="MariaDB",
                order=3,
                type="sql",
                driver="mariadb",
                required_fields=("type", "driver", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to MariaDB using a SQLAlchemy connection string.",
            ),
            ConnectorSpec(
                id="sql-server",
                group="databases",
                label="SQL Server",
                order=4,
                type="sql",
                driver="mssql",
                required_fields=("type", "driver", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to SQL Server using a SQLAlchemy/ODBC connection string.",
            ),
            ConnectorSpec(
                id="oracle",
                group="databases",
                label="Oracle",
                order=5,
                type="sql",
                driver="oracle",
                required_fields=("type", "driver", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to Oracle using a SQLAlchemy connection string.",
            ),
            ConnectorSpec(
                id="mongodb",
                group="databases",
                label="MongoDB",
                order=6,
                type="nosql",
                driver="mongodb",
                required_fields=("type", "driver", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to MongoDB using a MongoDB URI.",
            ),
            ConnectorSpec(
                id="gcp-bigquery",
                group="cloud_warehouses",
                label="GCP BigQuery",
                order=1,
                type="warehouse",
                provider="gcp",
                service="bigquery",
                required_fields=("type", "provider", "service", "project_id"),
                optional_fields=("dataset", "credentials_path", "options"),
                help_text="Run SQL in BigQuery using service account JSON or ADC.",
            ),
            ConnectorSpec(
                id="aws-redshift",
                group="cloud_warehouses",
                label="AWS Redshift",
                order=2,
                type="warehouse",
                provider="aws",
                service="redshift",
                required_fields=("type", "provider", "service", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to Amazon Redshift with a SQLAlchemy connection string.",
            ),
            ConnectorSpec(
                id="azure-synapse",
                group="cloud_warehouses",
                label="Azure Synapse",
                order=3,
                type="warehouse",
                provider="azure",
                service="synapse",
                required_fields=("type", "provider", "service", "connection_string"),
                optional_fields=("options",),
                help_text="Connect to Azure Synapse using ODBC/SQLAlchemy connection string.",
            ),
            ConnectorSpec(
                id="snowflake",
                group="cloud_warehouses",
                label="Snowflake",
                order=4,
                type="warehouse",
                provider="snowflake",
                service="snowflake",
                required_fields=("type", "provider", "service"),
                optional_fields=(
                    "connection_string",
                    "account",
                    "user",
                    "password",
                    "warehouse",
                    "database",
                    "schema",
                    "role",
                    "options",
                ),
                help_text="Connect to Snowflake with SQLAlchemy URI or explicit account parameters.",
            ),
        ]
        self._by_id: dict[str, ConnectorSpec] = {spec.id: spec for spec in self._specs}

    def get_spec(self, connector_id: str) -> ConnectorSpec:
        try:
            return self._by_id[connector_id]
        except KeyError as exc:
            raise ConnectorConfigError(f"Unknown connector id: '{connector_id}'") from exc

    def list_groups(self) -> List[ConnectorGroup]:
        return sorted(self._groups, key=lambda group: group.order)

    def list_connectors(self, group_id: Optional[str] = None) -> List[ConnectorSpec]:
        specs = self._specs
        if group_id:
            specs = [spec for spec in specs if spec.group == group_id]
        return sorted(specs, key=lambda spec: (self._group_order(spec.group), spec.order))

    def grouped_ui_options(self) -> List[Dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for group in self.list_groups():
            connectors = self.list_connectors(group.id)
            result.append(
                {
                    "id": group.id,
                    "label": group.label,
                    "order": group.order,
                    "connectors": [
                        {
                            "id": connector.id,
                            "label": connector.label,
                            "order": connector.order,
                            "help_text": connector.help_text,
                        }
                        for connector in connectors
                    ],
                }
            )
        return result

    def to_config_schema(self, default: str = "csv") -> Dict[str, Any]:
        if default not in self._by_id:
            raise ConnectorConfigError(f"Unknown default connector id: '{default}'")
        catalog = {
            spec.id: {
                "id": spec.id,
                "group": spec.group,
                "label": spec.label,
                "type": spec.type,
                "driver": spec.driver,
                "provider": spec.provider,
                "service": spec.service,
                "required_fields": list(spec.required_fields),
                "optional_fields": list(spec.optional_fields),
                "help_text": spec.help_text,
                "order": spec.order,
            }
            for spec in self.list_connectors()
        }
        groups = {
            group.id: {
                "id": group.id,
                "label": group.label,
                "order": group.order,
                "connectors": [
                    connector.id for connector in self.list_connectors(group_id=group.id)
                ],
            }
            for group in self.list_groups()
        }
        return {
            "connectors": {
                "default": default,
                "catalog": catalog,
                "groups": groups,
            }
        }

    def _group_order(self, group_id: str) -> int:
        for group in self._groups:
            if group.id == group_id:
                return group.order
        return 999


REGISTRY = ConnectorRegistry()


def create_connector(connector_id: str, config: Dict[str, Any]) -> BaseConnector:
    """Create a connector instance for a registered connector id."""

    spec = REGISTRY.get_spec(connector_id)
    connector_config = dict(config)

    connector_mapping: dict[str, type[BaseConnector]] = {
        "csv": FileConnector,
        "json": FileConnector,
        "postgres": SQLConnector,
        "mysql": SQLConnector,
        "mariadb": SQLConnector,
        "sql-server": SQLConnector,
        "oracle": SQLConnector,
        "mongodb": MongoDBConnector,
        "gcp-bigquery": BigQueryConnector,
        "aws-redshift": SQLConnector,
        "azure-synapse": SQLConnector,
        "snowflake": SnowflakeConnector,
    }

    connector_cls = connector_mapping[connector_id]
    return connector_cls(connector_id=connector_id, config=connector_config, spec=spec)


def default_connectors_config() -> Dict[str, Any]:
    """Return the default connector config schema for application config files."""

    return REGISTRY.to_config_schema(default="csv")


def validate_connectors_config(config: Dict[str, Any]) -> None:
    """Validate top-level connectors schema shape and default connector presence."""

    connectors = config.get("connectors")
    if not isinstance(connectors, dict):
        raise ConnectorConfigError("Config must include 'connectors' dictionary.")

    default = connectors.get("default")
    catalog = connectors.get("catalog")
    groups = connectors.get("groups")

    if not isinstance(default, str) or not default:
        raise ConnectorConfigError("'connectors.default' must be a non-empty string.")
    if not isinstance(catalog, dict) or not catalog:
        raise ConnectorConfigError("'connectors.catalog' must be a non-empty dictionary.")
    if not isinstance(groups, dict) or not groups:
        raise ConnectorConfigError("'connectors.groups' must be a non-empty dictionary.")
    if default not in catalog:
        raise ConnectorConfigError(
            f"'connectors.default' ({default}) must be present in 'connectors.catalog'."
        )

    for group in REGISTRY.list_groups():
        if group.id not in groups:
            raise ConnectorConfigError(
                f"'connectors.groups' missing required group '{group.id}'."
            )


def get_grouped_connector_options() -> List[Dict[str, Any]]:
    """Return grouped connector options for UI rendering."""

    return REGISTRY.grouped_ui_options()
