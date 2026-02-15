# Data Profiling con Registro de Conectores

Proyecto para generar reportes **EDA (Exploratory Data Analysis)** con `dataprep.eda` y una capa de conectores extensible con validacion de esquema, fabrica y metadatos para UI.

## Que se implemento

- Registro central (`ConnectorRegistry`) con taxonomia y orden deterministico.
- Modelo `ConnectorSpec` con campos: `id`, `group`, `label`, `type`, `driver/provider/service`, `required_fields`, `optional_fields`.
- Fabrica `create_connector(connector_id, config)`.
- Interfaz comun por conector:
  - `connect()`
  - `read(query_or_path, **kwargs)`
  - `test_connection()`
- Esquema de configuracion con:
  - `connectors.default`
  - `connectors.catalog`
  - `connectors.groups`
- Metadatos de UI agrupados por orden con `get_grouped_connector_options()`.

## Taxonomia y orden

1. `file`
   - `csv` (CSV)
   - `json` (JSON)
2. `databases` (transactional)
   - `postgres` (Postgres)
   - `mysql` (MySQL)
   - `mariadb` (MariaDB)
   - `sql-server` (SQL Server)
   - `oracle` (Oracle)
   - `mongodb` (MongoDB)
3. `cloud_warehouses`
   - `gcp-bigquery` (GCP BigQuery)
   - `aws-redshift` (AWS Redshift)
   - `azure-synapse` (Azure Synapse)
   - `snowflake` (Snowflake)

## Estructura

```text
.
|-- main.py
|-- data_profiling/
|   |-- __init__.py
|   `-- connectors.py
|-- config_examples/
|   `-- connectors.example.yaml
|-- docs/
|   `-- config-schema.md
`-- tests/
    |-- test_connector_registry.py
    `-- test_connector_connections.py
```

## Uso rapido

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para pruebas:

```powershell
pip install .[test]
pytest
```

Ejecucion principal:

```powershell
python main.py
```

Variables de entorno soportadas por `main.py`:

```dotenv
DATA_SOURCE=csv|json|gcp-bigquery
FILE_NAME=diamonds_sample.csv
GCP_PROJECT_ID=tu-proyecto-gcp
GCP_DATASET=dataset_opcional
GCP_CREDENTIALS_PATH=/ruta/a/service-account.json
GCP_LOCATION=US
```

## Esquema de configuracion

Config minima:

```yaml
connectors:
  default: csv
  catalog: {}
  groups: {}
```

Ejemplo completo:

- `config_examples/connectors.example.yaml`

Referencia corta:

- `docs/config-schema.md`

## Dependencias opcionales por conector

Instala extras segun el conector que uses:

- Postgres: `pip install .[postgres]`
- MySQL: `pip install .[mysql]`
- MariaDB: `pip install .[mariadb]`
- SQL Server: `pip install .[sqlserver]`
- Oracle: `pip install .[oracle]`
- MongoDB: `pip install .[mongodb]`
- BigQuery: `pip install .[bigquery]`
- Redshift: `pip install .[redshift]`
- Synapse: `pip install .[synapse]`
- Snowflake: `pip install .[snowflake]`

Los imports son lazy: si falta una dependencia, se lanza un error claro indicando el extra a instalar.
