# Data Profiling con DataPrep

Proyecto para generar reportes de **EDA (Exploratory Data Analysis)** usando `dataprep.eda`, con fuente de datos configurable (CSV o BigQuery).

## Descripcion

El script principal (`main.py`) hace lo siguiente:

1. Lee datos desde una fuente configurable (`DATA_SOURCE`):
   - `csv` (por defecto)
   - `bigquery`

2. Usa un unico nombre de archivo (`FILE_NAME`):
   - Si `DATA_SOURCE=csv`: lee `input_csv_files/<FILE_NAME>`.
   - Si `DATA_SOURCE=bigquery`: lee `input_sql_queries/<FILE_NAME>`.
3. Ejecuta la consulta y construye el DataFrame.
4. Genera un reporte EDA en HTML con DataPrep.
5. Guarda el resultado en `ouput_eda_reports/`.
6. Abre el reporte automaticamente en el navegador.

## Estructura del proyecto

```text
.
|-- main.py
|-- input_csv_files/
|   `-- diamonds_sample.csv
|-- input_sql_queries/
|   `-- table_name.sql
`-- ouput_eda_reports/
    `-- diamonds_sample.html
```

## Requisitos

- Python 3.9+
- Entorno virtual (recomendado)
- Paquetes:
  - `pandas`
  - `dataprep`
  - `google-cloud-bigquery`
  - `db-dtypes`

## Instalacion

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pandas dataprep
pip install google-cloud-bigquery db-dtypes
```

## Uso

Configura variables en el archivo `.env` (recomendado):

```dotenv
DATA_SOURCE=csv|bigquery
FILE_NAME=diamonds_sample.csv
GCP_PROJECT_ID=tu-proyecto-gcp
GCP_LOCATION=US
```

Opcionalmente, tambien puedes configurarlas en PowerShell:

```powershell
$env:DATA_SOURCE = "csv|bigquery"
$env:FILE_NAME = "diamonds_sample.csv"  # o "table_name.sql" para BigQuery
$env:GCP_PROJECT_ID = "tu-proyecto-gcp"
$env:GCP_LOCATION = "US"        # Opcional
```

Luego ejecuta:

```powershell
python main.py
```

## Salida

- Reporte HTML generado en:

```text
ouput_eda_reports/<nombre_de_archivo_sin_extension>.html
```

## Ejemplo rapido

Con la configuracion por defecto para CSV y el archivo `input_csv_files/diamonds_sample.csv`, la ejecucion genera:

- `ouput_eda_reports/diamonds_sample.html`

## Elegir fuente de datos

- `DATA_SOURCE=csv`: usa `FILE_NAME` con extension `.csv`.
- `DATA_SOURCE=bigquery`: usa `FILE_NAME` con extension `.sql`.
- El titulo y nombre del reporte se construyen con el nombre sin extension.
