"""
PostgreSQL Module with Connection Pool

This module provides a connection pool for PostgreSQL databases.
Configuration is loaded from nl2py.conf under the [postgres] section.

Example configuration in nl2py.conf:
    [postgres]
    HOST=localhost
    PORT=5432
    DATABASE=mydb
    USER=postgres
    PASSWORD=secret
    MIN_CONNECTIONS=1
    MAX_CONNECTIONS=10

Usage in generated code:
    from nl2py.modules import PostgresModule

    # Initialize module (happens once per program)
    pg = PostgresModule.from_config(config_path="nl2py.conf")

    # Get a connection from the pool
    conn = pg.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers")
        results = cursor.fetchall()
    finally:
        pg.release_connection(conn)
"""

import configparser
import psycopg2
from psycopg2 import pool
from pathlib import Path
from typing import Optional
import threading
from .module_base import NL2PyModuleBase


class PostgresModule(NL2PyModuleBase):
    """
    PostgreSQL connection pool manager.

    This class manages a pool of connections to a PostgreSQL database,
    allowing efficient reuse of connections across multiple operations.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, host: str, port: int, database: str, user: str,
                 password: str, min_connections: int = 1, max_connections: int = 10):
        """
        Initialize the PostgreSQL connection pool.

        Args:
            host: Database host address
            port: Database port (typically 5432)
            database: Database name
            user: Username for authentication
            password: Password for authentication
            min_connections: Minimum number of connections in pool
            max_connections: Maximum number of connections in pool
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.min_connections = min_connections
        self.max_connections = max_connections

        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                min_connections,
                max_connections,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            print(f"[PostgresModule] Connection pool created: {database}@{host}:{port}")
        except psycopg2.Error as e:
            raise RuntimeError(f"Failed to create PostgreSQL connection pool: {e}")

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf") -> 'PostgresModule':
        """
        Create a PostgresModule from configuration file.
        Uses singleton pattern to ensure only one pool exists.

        Args:
            config_path: Path to nl2py.conf file

        Returns:
            PostgresModule instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            KeyError: If required configuration is missing
        """
        with cls._lock:
            if cls._instance is None:
                config = configparser.ConfigParser()
                path = Path(config_path)

                if not path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_path}")

                config.read(path)

                if 'postgres' not in config:
                    raise KeyError("Missing [postgres] section in nl2py.conf")

                pg_config = config['postgres']

                # Required fields
                host = pg_config.get('HOST')
                port = pg_config.getint('PORT', 5432)
                database = pg_config.get('DATABASE')
                user = pg_config.get('USER')
                password = pg_config.get('PASSWORD')

                # Optional fields
                min_conn = pg_config.getint('MIN_CONNECTIONS', 1)
                max_conn = pg_config.getint('MAX_CONNECTIONS', 10)

                if not all([host, database, user, password]):
                    raise KeyError("Missing required postgres configuration: HOST, DATABASE, USER, PASSWORD")

                cls._instance = cls(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    min_connections=min_conn,
                    max_connections=max_conn
                )

            return cls._instance

    def get_connection(self):
        """
        Get a connection from the pool.

        Returns:
            psycopg2.connection: A database connection

        Raises:
            RuntimeError: If unable to get connection from pool
        """
        try:
            conn = self.connection_pool.getconn()
            if conn:
                return conn
            else:
                raise RuntimeError("Unable to get connection from pool")
        except psycopg2.Error as e:
            raise RuntimeError(f"Error getting connection: {e}")

    def release_connection(self, conn):
        """
        Release a connection back to the pool.

        Args:
            conn: The connection to release
        """
        if conn:
            self.connection_pool.putconn(conn)

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """
        Execute a query using a connection from the pool.
        Automatically handles connection acquisition and release.

        Args:
            query: SQL query to execute
            params: Optional parameters for parameterized query
            fetch: If True, fetch and return results (for SELECT)

        Returns:
            List of rows if fetch=True, None otherwise

        Example:
            results = pg.execute_query("SELECT * FROM users WHERE age > %s", (25,))
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch:
                results = cursor.fetchall()
                return results
            else:
                conn.commit()
                return None
        except psycopg2.Error as e:
            conn.rollback()
            raise RuntimeError(f"Query execution failed: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)

    def execute_many(self, query: str, params_list: list):
        """
        Execute the same query multiple times with different parameters.
        Useful for batch inserts.

        Args:
            query: SQL query to execute
            params_list: List of parameter tuples

        Example:
            pg.execute_many(
                "INSERT INTO users (name, age) VALUES (%s, %s)",
                [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
            )
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            raise RuntimeError(f"Batch execution failed: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)

    def close_all_connections(self):
        """
        Close all connections in the pool.
        Should be called when the program terminates.
        """
        if self.connection_pool:
            self.connection_pool.closeall()
            print("[PostgresModule] All connections closed")

    def __del__(self):
        """Destructor to ensure connections are closed."""
        self.close_all_connections()

    def get_pool_status(self) -> dict:
        """
        Get current status of the connection pool.

        Returns:
            dict: Pool statistics
        """
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections
        }

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="PostgreSQL",
            task_type="postgres",
            description="PostgreSQL relational database with connection pooling, transactions, and parameterized queries",
            version="1.0.0",
            keywords=[
                "postgresql", "postgres", "sql", "database", "relational",
                "connection-pool", "transactions", "queries", "psycopg2"
            ],
            dependencies=["psycopg2-binary>=2.9.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern with threaded connection pool",
            "Default port is 5432 for PostgreSQL",
            "MIN_CONNECTIONS defaults to 1, MAX_CONNECTIONS defaults to 10",
            "Connections automatically returned to pool after use",
            "execute_query() handles connection management automatically",
            "Use fetch=True for SELECT queries, fetch=False for INSERT/UPDATE/DELETE",
            "Parameterized queries prevent SQL injection (use %s placeholders)",
            "execute_many() efficient for batch inserts (single query, multiple params)",
            "Transactions auto-commit on success, auto-rollback on error",
            "get_connection() retrieves from pool, release_connection() returns it",
            "Always release connections to avoid pool exhaustion",
            "Connection pool is thread-safe for concurrent operations",
            "Cursor closed automatically after execute_query() completes",
            "close_all_connections() called automatically on program exit",
            "Use context managers with manual connection management for complex transactions",
            "Query results returned as list of tuples by default",
            "psycopg2.Error exceptions wrapped in RuntimeError with details",
            "Connection pool creates connections lazily up to max_connections",
            "Database schema must exist before connection",
            "SSL/TLS support via psycopg2 connection parameters (add to __init__ if needed)"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="execute_query",
                description="Execute SQL query with automatic connection management",
                parameters={
                    "query": "str (required) - SQL query with %s placeholders for params",
                    "params": "tuple (optional) - Parameters for parameterized query",
                    "fetch": "bool (optional) - True for SELECT (default), False for INSERT/UPDATE/DELETE"
                },
                returns="list - List of tuples (rows) if fetch=True, None otherwise",
                examples=[
                    {"text": "Select all users from users table", "code": "execute_query(query='SELECT * FROM users')"},
                    {"text": "Select users older than {{age}}", "code": "execute_query(query='SELECT * FROM users WHERE age > %s', params=({{age}},))"},
                    {"text": "Insert user {{name}} with age {{age}}", "code": "execute_query(query='INSERT INTO users (name, age) VALUES (%s, %s)', params=('{{name}}', {{age}}), fetch=False)"}
                ]
            ),
            MethodInfo(
                name="execute_many",
                description="Execute same query multiple times with different parameters (batch operation)",
                parameters={
                    "query": "str (required) - SQL query with %s placeholders",
                    "params_list": "list (required) - List of parameter tuples"
                },
                returns="None",
                examples=[
                    {"text": "Batch insert users from {{user_list}}", "code": "execute_many(query='INSERT INTO users (name, age) VALUES (%s, %s)', params_list={{user_list}})"}
                ]
            ),
            MethodInfo(
                name="get_connection",
                description="Get a connection from the pool for manual management",
                parameters={},
                returns="psycopg2.connection - Database connection object",
                examples=[
                    {"text": "Get a database connection from the pool", "code": "get_connection()"}
                ]
            ),
            MethodInfo(
                name="release_connection",
                description="Release a connection back to the pool",
                parameters={"conn": "connection (required) - Connection to release"},
                returns="None",
                examples=[
                    {"text": "Release connection {{connection}} back to pool", "code": "release_connection(conn={{connection}})"}
                ]
            ),
            MethodInfo(
                name="get_pool_status",
                description="Get current connection pool configuration and status",
                parameters={},
                returns="dict - Pool statistics including host, port, database, min/max connections",
                examples=[
                    {"text": "Get the current connection pool status", "code": "get_pool_status()"}
                ]
            ),
            MethodInfo(
                name="close_all_connections",
                description="Close all connections in the pool (called automatically on exit)",
                parameters={},
                returns="None",
                examples=[
                    {"text": "Close all connections in the pool", "code": "close_all_connections()"}
                ]
            )
        ]

