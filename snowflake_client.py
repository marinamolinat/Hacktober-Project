"""One serialized Snowflake connection for the single-process hackathon backend."""

import os
import re
import threading
from contextlib import contextmanager


LOCK = threading.RLock()


class SnowflakeUnavailable(RuntimeError):
    pass


def configured():
    if os.getenv("STORAGE_BACKEND", "").lower() == "sqlite":
        return False
    return os.getenv("STORAGE_BACKEND", "").lower() == "snowflake" or bool(os.getenv("SNOWFLAKE_ACCOUNT"))


def identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", value or ""):
        raise ValueError("Invalid configured Snowflake object name")
    return value.upper()


class SnowflakeClient:
    def __init__(self):
        self.connection = None
        self.error = None

    def connect(self):
        with LOCK:
            if self.connection is not None and not self.connection.is_closed():
                return self.connection
            if not os.getenv("SNOWFLAKE_ACCOUNT") or not os.getenv("SNOWFLAKE_USER"):
                self.error = "Set SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER in the local environment."
                raise SnowflakeUnavailable(self.error)
            try:
                import snowflake.connector
                options = {
                    "account": os.environ["SNOWFLAKE_ACCOUNT"],
                    "user": os.environ["SNOWFLAKE_USER"],
                    "warehouse": identifier(os.getenv("SNOWFLAKE_WAREHOUSE", "HACKATHON_APP_WH")),
                    "database": identifier(os.getenv("SNOWFLAKE_DATABASE", "HACKATHON_DB")),
                    "schema": identifier(os.getenv("SNOWFLAKE_SCHEMA", "APP")),
                    "role": identifier(os.getenv("SNOWFLAKE_ROLE", "HACKATHON_API")),
                    "login_timeout": 45,
                    "network_timeout": 45,
                    "autocommit": True,
                    "session_parameters": {"TIMEZONE": "UTC", "STATEMENT_TIMEOUT_IN_SECONDS": 45},
                }
                authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser")
                key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
                if key_path:
                    options["authenticator"] = "SNOWFLAKE_JWT"
                    options["private_key_file"] = os.path.expanduser(key_path)
                    passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
                    if passphrase:
                        options["private_key_file_pwd"] = passphrase
                else:
                    options["authenticator"] = authenticator
                    if authenticator == "snowflake":
                        options["password"] = os.getenv("SNOWFLAKE_PASSWORD", "")
                    elif authenticator == "oauth":
                        options["token"] = os.getenv("SNOWFLAKE_OAUTH_TOKEN", "")
                self.connection = snowflake.connector.connect(**options)
                self.error = None
                return self.connection
            except SnowflakeUnavailable:
                raise
            except Exception as exc:
                self.error = "Snowflake connection failed. Check account, authentication, role, and setup."
                raise SnowflakeUnavailable(self.error) from exc

    @contextmanager
    def session(self, transaction=False, role=None):
        with LOCK:
            connection = self.connect()
            default_role = identifier(os.getenv("SNOWFLAKE_ROLE", "HACKATHON_API"))
            try:
                if role:
                    with connection.cursor() as cursor:
                        cursor.execute(f"USE ROLE {identifier(role)}")
                if transaction:
                    with connection.cursor() as cursor:
                        cursor.execute("BEGIN")
                yield connection
                if transaction:
                    connection.commit()
            except Exception:
                if transaction:
                    connection.rollback()
                raise
            finally:
                if role:
                    with connection.cursor() as cursor:
                        cursor.execute(f"USE ROLE {default_role}")

    def complete(self, prompt, model=None):
        model = model or os.getenv("SNOWFLAKE_EXTRACT_MODEL") or os.getenv("CORTEX_MODEL")
        if not model:
            raise SnowflakeUnavailable("Choose an enabled model and set SNOWFLAKE_EXTRACT_MODEL.")
        try:
            with self.session(role=os.getenv("SNOWFLAKE_INGEST_ROLE", "HACKATHON_INGEST")) as connection, connection.cursor() as cursor:
                cursor.execute("SELECT AI_COMPLETE(%s, %s)", (model, prompt))
                value = cursor.fetchone()[0]
                if value is None:
                    raise SnowflakeUnavailable("The configured Cortex model did not return a result.")
                return value
        except SnowflakeUnavailable:
            raise
        except Exception as exc:
            raise SnowflakeUnavailable("Cortex inference failed. Check the enabled model and AI privileges.") from exc

    def search(self, query, limit=100):
        from snowflake.core import Root

        database = identifier(os.getenv("SNOWFLAKE_DATABASE", "HACKATHON_DB"))
        schema = identifier(os.getenv("SNOWFLAKE_SCHEMA", "APP"))
        service = os.getenv("SNOWFLAKE_SEARCH_SERVICE", "EVENT_SEARCH").split(".")
        if len(service) == 3:
            database, schema, name = map(identifier, service)
        elif len(service) == 1:
            name = identifier(service[0])
        else:
            raise ValueError("SNOWFLAKE_SEARCH_SERVICE must be a name or database.schema.name")
        try:
            with self.session() as connection:
                resource = Root(connection).databases[database].schemas[schema].cortex_search_services[name]
                response = resource.search(query=query, columns=["EVENT_ID"], limit=min(100, limit))
                return [row.get("EVENT_ID") or row.get("event_id") for row in response.results]
        except Exception as exc:
            raise SnowflakeUnavailable("Cortex Search is unavailable; using current database candidates.") from exc

    def status(self):
        connected = self.connection is not None and not self.connection.is_closed()
        return {"backend": "snowflake", "connected": connected, "error": self.error}


_client = SnowflakeClient()


def get_client():
    return _client
