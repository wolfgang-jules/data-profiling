"""Generate YData profiling reports from registered connectors."""

import os
import webbrowser
import importlib
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from data_profiling.connectors import create_connector

BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV_DIR = BASE_DIR / "input" / "csv_files"
INPUT_SQL_DIR = BASE_DIR / "input" / "sql_files"
OUTPUT_REPORTS_DIR = BASE_DIR / "output" / "ydata"


def load_env_file(env_path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into environment variables."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_env_var(name: str, default: Optional[str] = None, required: bool = False) -> str:
    """Return an environment variable value with optional required validation."""
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value if value is not None else ""


def normalize_connector_id(source_type: str) -> str:
    """Normalize source type text to stable connector ids."""
    return source_type.lower().strip()


def get_input_file_path(connector_id: str, file_name: str) -> Path:
    """Return the input file path validating extension by connector id."""
    source = connector_id.lower().strip()
    file_path = Path(file_name)
    suffix = file_path.suffix.lower()

    if source == "csv":
        expected_suffix = ".csv"
        input_dir = INPUT_CSV_DIR
    elif source == "json":
        expected_suffix = ".json"
        input_dir = INPUT_CSV_DIR
    elif source == "gcp-bigquery":
        expected_suffix = ".sql"
        input_dir = INPUT_SQL_DIR
    else:
        raise ValueError(
            "Unsupported source type. Use one of: 'csv', 'json', 'gcp-bigquery'."
        )

    if suffix != expected_suffix:
        raise ValueError(
            f"FILE_NAME must end with '{expected_suffix}' when DATA_SOURCE='{connector_id}'. "
            f"Received: {file_name}"
        )

    resolved_file_path = input_dir / file_path.name
    if not resolved_file_path.exists():
        raise FileNotFoundError(f"Input file not found: {resolved_file_path}")

    return resolved_file_path


def build_connector_config(connector_id: str, file_name: str) -> dict[str, Any]:
    """Build connector-specific configuration from environment variables."""
    if connector_id == "csv":
        return {
            "type": "file",
            "format": "csv",
            "path": str(get_input_file_path(connector_id=connector_id, file_name=file_name)),
            "options": {},
        }
    if connector_id == "json":
        return {
            "type": "file",
            "format": "json",
            "path": str(get_input_file_path(connector_id=connector_id, file_name=file_name)),
            "options": {},
        }
    if connector_id == "gcp-bigquery":
        return {
            "type": "warehouse",
            "provider": "gcp",
            "service": "bigquery",
            "project_id": get_env_var("GCP_PROJECT_ID", required=True),
            "dataset": get_env_var("GCP_DATASET", default=""),
            "credentials_path": get_env_var("GCP_CREDENTIALS_PATH", default=""),
            "options": {"location": get_env_var("GCP_LOCATION", default="") or None},
        }

    raise ValueError(f"Unsupported connector id: {connector_id}")


def load_dataframe(connector_id: str, file_name: str) -> pd.DataFrame:
    """Load a dataframe using the selected connector."""
    normalized_id = normalize_connector_id(connector_id)
    connector_config = build_connector_config(normalized_id, file_name)
    connector = create_connector(normalized_id, connector_config)

    if normalized_id in {"csv", "json"}:
        file_path = get_input_file_path(connector_id=normalized_id, file_name=file_name)
        return connector.read(str(file_path))

    if normalized_id == "gcp-bigquery":
        sql_path = get_input_file_path(connector_id=normalized_id, file_name=file_name)
        query = sql_path.read_text(encoding="utf-8")
        return connector.read(query)

    raise ValueError(f"Unsupported connector id: {normalized_id}")


def open_report(report_html_path: Path) -> None:
    """Open generated report in browser using file URI."""
    webbrowser.open(report_html_path.resolve().as_uri(), new=2)


def get_profile_report_class() -> Any:
    """Return ydata ProfileReport class with clear dependency error."""
    try:
        module = importlib.import_module("ydata_profiling")
    except ImportError as exc:
        raise ImportError(
            "Missing dependency 'ydata-profiling'. Install with: "
            "pip install -r requirements_ydata.txt"
        ) from exc
    return module.ProfileReport


def main() -> None:
    """Generate ydata-profiling report from configured data source."""
    load_env_file(BASE_DIR / ".env")

    source_type = get_env_var("DATA_SOURCE", default="csv")
    file_name = get_env_var("FILE_NAME", default="costumers.csv")
    file_stem = Path(file_name).stem

    df = load_dataframe(connector_id=source_type, file_name=file_name)

    OUTPUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_html_path = OUTPUT_REPORTS_DIR / f"{file_stem}_profiling.html"

    title = f'Exploratory Data Analysis ("{file_stem}")'
    profile_report_cls = get_profile_report_class()
    profile = profile_report_cls(df, title=title, explorative=True)
    profile.to_file(str(report_html_path))
    open_report(report_html_path)


if __name__ == "__main__":
    main()
