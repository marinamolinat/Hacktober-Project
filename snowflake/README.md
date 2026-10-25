# Snowflake setup

The package creates the 11 tables in `HACKATHON_DB.APP`, scoped runtime roles,
two small warehouses, and optionally the public event Search service and Agent.
The files have been prepared locally; account execution and index readiness are
separate steps. No inference model is assumed to have been tested.

## Quick setup from the project folder

1. Install the project's requirements and put these nonsecret account settings in
   the server's local `.env`:

   ```dotenv
   SNOWFLAKE_ACCOUNT=OIDSFET-UM90636
   SNOWFLAKE_USER=OPATIENCE
   SNOWFLAKE_AUTHENTICATOR=externalbrowser
   SNOWFLAKE_DATABASE=HACKATHON_DB
   SNOWFLAKE_SCHEMA=APP
   SNOWFLAKE_WAREHOUSE=HACKATHON_APP_WH
   SNOWFLAKE_ROLE=HACKATHON_API
   SNOWFLAKE_INGEST_ROLE=HACKATHON_INGEST
   ```

2. Review the selected files without connecting:

   ```bash
   python snowflake/apply.py --seed-tags --seed-clubs
   ```

3. Apply the storage setup. This opens a Snowflake browser login using your
   administrator session, creates resources, and stops at the first error:

   ```bash
   python snowflake/apply.py --apply --seed-tags --seed-clubs --status
   ```

4. If you want Search and Agent enabled, review `004_search_agent.sql` and run:

   ```bash
   python snowflake/apply.py --apply --include-search --status
   ```

   This starts billable indexing and serving. Initial indexing may take several
   minutes. A created object does not prove that it is ready or returns results.

5. Choose an inference model available in this account and configure
   `SNOWFLAKE_EXTRACT_MODEL` / `SNOWFLAKE_SUMMARY_MODEL` (or the app's `CORTEX_MODEL`
   compatibility setting). Model inference is not called by the setup CLI.

The account inspection supplied by the owner reports `AWS_US_EAST_2` (Ohio).
[Cortex Search is supported in that region](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview).
Account model permissions and routing policy still determine inference access.
The setup reports `CORTEX_ENABLED_CROSS_REGION` without changing it.

## Files and effects

| File | Effect |
| --- | --- |
| `001_bootstrap.sql` | Creates owner/API/ingest roles, database/schema, and two auto-suspending XSMALL warehouses; grants Cortex access. |
| `002_schema.sql` | Creates exactly 11 standard base tables. |
| `003_access.sql` | Grants explicit table permissions. Ingest cannot read private users, preferences or follows. |
| `004_search_agent.sql` | Optionally creates `EVENT_SEARCH` and `EVENT_ASSISTANT`, with API usage grants. |
| `005_smoke.sql` | Read-only manual account/schema inspection; it is never run automatically. |
| `006_service_users.sql.template` | Public-key-only templates for separate unattended runtime identities. |
| `seed_tags.sql` | Optionally merges the curated vocabulary; it creates no clubs or event facts. |
| `seed_clubs.sql` | Optionally merges the reviewed real club/account mappings; it creates no posts or event facts. |
| `apply.py` | Explicit apply/status CLI, fail-fast execution, single-runner lock, external JSONL deployment record. |

Tags use their stable slug as `TAG_ID`, matching runtime storage. No twelfth join
or deployment-history table is introduced. PK, FK and UNIQUE declarations on
Snowflake standard tables are informational; the serialized application writer
must enforce them. `NOT NULL` is enforced.

The setup CLI records file hashes, outcomes and query IDs in
`/tmp/snowflask-setup.jsonl` by default, outside application tables. Set
`--log-path` for a different local record. It excludes SQL results, secrets and
user payloads. DDL statements commit separately, so completed statements remain
if a later statement fails. Re-running the initial files preserves existing
objects and records; `IF NOT EXISTS` does not alter old table definitions.

## Authentication

Browser authentication is convenient for a local administrator. Production
processes use separate `HACKATHON_API_SERVICE` and `HACKATHON_INGEST_SERVICE`
identities and key pairs. Keep private keys outside this repository and put only
the public-key body into the reviewed template. The CLI also accepts an existing
`SNOWFLAKE_CONNECTION_NAME`, or `SNOWFLAKE_PRIVATE_KEY_PATH` with optional
`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`. It never prints their contents.

The API role reads public content and manages scoped user records. The ingestion
role writes public posts/events. The owner curates clubs, club mappings and tags.
Do not widen API privileges to seed clubs; use an explicit owner operation.

Direct Search/Agent REST calls require an actual Snowflake OAuth token, PAT or
signed key-pair JWT with its correct authorization type. Connector browser login
does not provide a supported reusable REST bearer token for the app.

## Readiness and shutdown

`python snowflake/apply.py --status` reads account/table/object status without
creating resources or invoking a model. Inspect Search service readiness with:

```sql
USE ROLE HACKATHON_OWNER;
DESCRIBE CORTEX SEARCH SERVICE HACKATHON_DB.APP.EVENT_SEARCH;
```

`indexing_state`, `indexing_error`, `serving_state`, `source_data_num_rows` and
`data_timestamp` distinguish object creation from an available, populated index.
The application must recheck current event facts, eligibility and sources after
retrieval because indexed facts can lag.

To stop Search and its warehouses when the project is not being used:

```sql
USE ROLE HACKATHON_OWNER;
ALTER CORTEX SEARCH SERVICE HACKATHON_DB.APP.EVENT_SEARCH SUSPEND;
ALTER WAREHOUSE HACKATHON_APP_WH SUSPEND;
ALTER WAREHOUSE HACKATHON_SEARCH_WH SUSPEND;
```

Stop application inference calls too. Warehouse suspension alone does not stop
Search serving or AI charges. Resume the Search service before querying it again.

## Official references

- [Search creation and permissions](https://docs.snowflake.com/en/sql-reference/sql/create-cortex-search)
- [Agent creation and specification](https://docs.snowflake.com/en/sql-reference/sql/create-agent)
- [Cortex inference permissions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql-privileges-and-access)
- [Agent authentication and tool access](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-setup)
- [Python connector script execution](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-api)

Syntax and access requirements were checked against official documentation on
2026-10-25. No account SQL or inference tests were run while preparing these files.
