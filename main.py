"""Generate DataPrep EDA reports from CSV files or BigQuery SQL files."""

import os
import webbrowser
from pathlib import Path
from typing import Optional

import pandas as pd
from dataprep.eda.create_report import create_report
from google.cloud import bigquery

BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV_DIR = BASE_DIR / "input_csv_files"
INPUT_SQL_DIR = BASE_DIR / "input_sql_queries"
OUTPUT_REPORTS_DIR = BASE_DIR / "ouput_eda_reports"


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


def get_input_file_path(source_type: str, file_name: str) -> Path:
    """Return the input file path validating extension by source type."""
    source = source_type.lower().strip()
    file_path = Path(file_name)
    suffix = file_path.suffix.lower()

    if source == "csv":
        expected_suffix = ".csv"
        input_dir = INPUT_CSV_DIR
    elif source == "bigquery":
        expected_suffix = ".sql"
        input_dir = INPUT_SQL_DIR
    else:
        raise ValueError(f"Unsupported source type: {source_type}. Use 'csv' or 'bigquery'.")

    if suffix != expected_suffix:
        raise ValueError(
            f"FILE_NAME must end with '{expected_suffix}' when DATA_SOURCE='{source}'. "
            f"Received: {file_name}"
        )

    resolved_file_path = input_dir / file_path.name
    if not resolved_file_path.exists():
        raise FileNotFoundError(f"Input file not found: {resolved_file_path}")

    return resolved_file_path


def load_dataframe_from_csv(csv_path: Path) -> pd.DataFrame:
    """Load a dataframe from a CSV file path."""
    return pd.read_csv(csv_path)


def load_dataframe_from_bigquery(sql_path: Path) -> pd.DataFrame:
    """Load a dataframe executing a SQL file in BigQuery."""
    project_id = get_env_var("GCP_PROJECT_ID", required=True)
    location = os.getenv("GCP_LOCATION")
    query = sql_path.read_text(encoding="utf-8")

    client = bigquery.Client(project=project_id)
    query_job = client.query(query=query, location=location)
    return query_job.result().to_dataframe()


def load_dataframe(source_type: str, file_name: str) -> pd.DataFrame:
    """Select source loader based on source type."""
    input_file_path = get_input_file_path(source_type=source_type, file_name=file_name)
    source = source_type.lower().strip()
    if source == "csv":
        return load_dataframe_from_csv(input_file_path)
    if source == "bigquery":
        return load_dataframe_from_bigquery(input_file_path)
    raise ValueError(f"Unsupported source type: {source_type}. Use 'csv' or 'bigquery'.")


def open_report(report_html_path: Path) -> None:
    """Open generated report in browser using file URI."""
    webbrowser.open(report_html_path.resolve().as_uri(), new=2)


def main() -> None:
    """Generate EDA report from configured data source."""
    load_env_file(BASE_DIR / ".env")

    source_type = get_env_var("DATA_SOURCE", default="csv")
    file_name = get_env_var("FILE_NAME", default="diamonds_sample.csv")
    file_stem = Path(file_name).stem

    df = load_dataframe(source_type=source_type, file_name=file_name)

    OUTPUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_base_path = OUTPUT_REPORTS_DIR / file_stem
    report_html_path = report_base_path.with_suffix(".html")

    title = f'Exploratory Data Analysis ("{file_stem}" )'
    report = create_report(df, title=title)
    report.save(str(report_base_path))
    open_report(report_html_path)

if __name__ == "__main__":
    main()
