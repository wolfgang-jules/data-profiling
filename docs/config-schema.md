# Esquema de configuracion de conectores

El proyecto soporta un registro de conectores con IDs estables y orden deterministico para UI.

## Formato esperado

```yaml
connectors:
  default: csv
  catalog: {}
  groups: {}
```

- `connectors.default`: ID del conector por defecto. Debe ser `csv` por defecto.
- `connectors.catalog`: diccionario de definiciones por ID estable.
- `connectors.groups`: metadatos para agrupacion y orden de UI.

## IDs estables

- File: `csv`, `json`
- Databases: `postgres`, `mysql`, `mariadb`, `sql-server`, `oracle`, `mongodb`
- Cloud warehouses: `gcp-bigquery`, `aws-redshift`, `azure-synapse`, `snowflake`

## Orden fijo de grupos y conectores

1. `file`: `csv`, `json`
2. `databases`: `postgres`, `mysql`, `mariadb`, `sql-server`, `oracle`, `mongodb`
3. `cloud_warehouses`: `gcp-bigquery`, `aws-redshift`, `azure-synapse`, `snowflake`

## API principal

- `ConnectorSpec`: metadatos del conector.
- `ConnectorRegistry`: registro con orden deterministico.
- `create_connector(connector_id, config)`: fabrica de conectores.
- `get_grouped_connector_options()`: opciones agrupadas para UI.
- `default_connectors_config()`: esquema por defecto listo para serializar.
- `validate_connectors_config(config)`: validacion basica del schema.

## Ejemplo completo

Ver `config_examples/connectors.example.yaml`.
