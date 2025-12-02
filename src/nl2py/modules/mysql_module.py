"""
MySQL Module with Connection Pool

This module provides a connection pool for MySQL/MariaDB databases.
Configuration is loaded from nl2py.conf under the [mysql] section.

Example configuration in nl2py.conf:
    [mysql]
    HOST=localhost
    PORT=3306
    DATABASE=mydb
    USER=root
    PASSWORD=secret
    MIN_CONNECTIONS=1
    MAX_CONNECTIONS=10
    CHARSET=utf8mb4

Usage in generated code:
    from nl2py.modules import MySQLModule

    # Initialize module (happens once per program)
    mysql = MySQLModule.from_config(config_path="nl2py.conf")

    # Get a connection from the pool
    conn = mysql.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers")
        results = cursor.fetchall()
    finally:
        mysql.release_connection(conn)
"""

import configparser
import mysql.connector
from mysql.connector import pooling, Error
from pathlib import Path
from typing import Optional, List, Tuple, Any
import threading
from .module_base import NL2PyModuleBase


class MySQLModule(NL2PyModuleBase):
    """
    MySQL connection pool manager.

    This class manages a pool of connections to a MySQL/MariaDB database,
    allowing efficient reuse of connections across multiple operations.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, host: str, port: int, database: str, user: str,
                 password: str, min_connections: int = 1, max_connections: int = 10,
                 charset: str = "utf8mb4"):
        """
        Initialize the MySQL connection pool.

        Args:
            host: Database host address
            port: Database port (typically 3306)
            database: Database name
            user: Username for authentication
            password: Password for authentication
            min_connections: Minimum number of connections in pool
            max_connections: Maximum number of connections in pool
            charset: Character set (default: utf8mb4)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.charset = charset

        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="aibasic_mysql_pool",
                pool_size=max_connections,
                pool_reset_session=True,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                charset=charset,
                autocommit=False
            )
            print(f"[MySQLModule] Connection pool created: {database}@{host}:{port}")
        except Error as e:
            raise RuntimeError(f"Failed to create MySQL connection pool: {e}")

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf") -> 'MySQLModule':
        """
        Create a MySQLModule from configuration file.
        Uses singleton pattern to ensure only one pool exists.

        Args:
            config_path: Path to nl2py.conf file

        Returns:
            MySQLModule instance

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

                if 'mysql' not in config:
                    raise KeyError("Missing [mysql] section in nl2py.conf")

                mysql_config = config['mysql']

                # Required fields
                host = mysql_config.get('HOST')
                port = mysql_config.getint('PORT', 3306)
                database = mysql_config.get('DATABASE')
                user = mysql_config.get('USER')
                password = mysql_config.get('PASSWORD')

                # Optional fields
                min_conn = mysql_config.getint('MIN_CONNECTIONS', 1)
                max_conn = mysql_config.getint('MAX_CONNECTIONS', 10)
                charset = mysql_config.get('CHARSET', 'utf8mb4')

                if not all([host, database, user, password]):
                    raise KeyError("Missing required mysql configuration: HOST, DATABASE, USER, PASSWORD")

                cls._instance = cls(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    min_connections=min_conn,
                    max_connections=max_conn,
                    charset=charset
                )

            return cls._instance

    def get_connection(self):
        """
        Get a connection from the pool.

        Returns:
            mysql.connector.connection: A database connection

        Raises:
            RuntimeError: If unable to get connection from pool
        """
        try:
            conn = self.connection_pool.get_connection()
            if conn:
                return conn
            else:
                raise RuntimeError("Unable to get connection from pool")
        except Error as e:
            raise RuntimeError(f"Error getting connection: {e}")

    def release_connection(self, conn):
        """
        Release a connection back to the pool.

        Args:
            conn: The connection to release
        """
        if conn and conn.is_connected():
            conn.close()  # Returns to pool when using pooling

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[List[Tuple]]:
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
            results = mysql.execute_query("SELECT * FROM users WHERE age > %s", (25,))
        """
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch:
                results = cursor.fetchall()
                return results
            else:
                conn.commit()
                return None
        except Error as e:
            if conn:
                conn.rollback()
            raise RuntimeError(f"Query execution failed: {e}")
        finally:
            if cursor:
                cursor.close()
            self.release_connection(conn)

    def execute_query_dict(self, query: str, params: tuple = None) -> Optional[List[dict]]:
        """
        Execute a query and return results as list of dictionaries.
        Each row is a dict with column names as keys.

        Args:
            query: SQL query to execute
            params: Optional parameters for parameterized query

        Returns:
            List of dictionaries, one per row

        Example:
            results = mysql.execute_query_dict("SELECT * FROM users WHERE age > %s", (25,))
            # [{'id': 1, 'name': 'Alice', 'age': 30}, ...]
        """
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            results = cursor.fetchall()
            return results
        except Error as e:
            raise RuntimeError(f"Query execution failed: {e}")
        finally:
            if cursor:
                cursor.close()
            self.release_connection(conn)

    def execute_many(self, query: str, params_list: List[tuple]):
        """
        Execute the same query multiple times with different parameters.
        Useful for batch inserts.

        Args:
            query: SQL query to execute
            params_list: List of parameter tuples

        Example:
            mysql.execute_many(
                "INSERT INTO users (name, age) VALUES (%s, %s)",
                [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
            )
        """
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
        except Error as e:
            if conn:
                conn.rollback()
            raise RuntimeError(f"Batch execution failed: {e}")
        finally:
            if cursor:
                cursor.close()
            self.release_connection(conn)

    def call_procedure(self, proc_name: str, args: tuple = ()) -> Optional[List[Any]]:
        """
        Call a stored procedure.

        Args:
            proc_name: Name of the stored procedure
            args: Arguments to pass to the procedure

        Returns:
            Results from the procedure

        Example:
            results = mysql.call_procedure('get_user_orders', (user_id,))
        """
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.callproc(proc_name, args)

            # Fetch results if any
            results = []
            for result in cursor.stored_results():
                results.extend(result.fetchall())

            conn.commit()
            return results if results else None
        except Error as e:
            if conn:
                conn.rollback()
            raise RuntimeError(f"Procedure call failed: {e}")
        finally:
            if cursor:
                cursor.close()
            self.release_connection(conn)

    def get_pool_status(self) -> dict:
        """
        Get current status of the connection pool.

        Returns:
            dict: Pool statistics and configuration
        """
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "charset": self.charset,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "pool_name": "aibasic_mysql_pool"
        }

    def close_all_connections(self):
        """
        Close all connections in the pool.
        Should be called when the program terminates.

        Note: With mysql.connector pooling, connections are automatically
        managed, but we provide this for consistency.
        """
        print("[MySQLModule] Connection pool cleanup")

    def __del__(self):
        """Destructor to ensure connections are closed."""
        self.close_all_connections()

    # ========================================
    # Metadata methods for NL2Py compiler
    # ========================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="MySQL",
            task_type="mysql",
            description="MySQL/MariaDB relational database with connection pooling, SQL query execution, and stored procedure support",
            version="1.0.0",
            keywords=[
                "mysql", "mariadb", "sql", "database", "relational", "query",
                "connection-pool", "stored-procedure", "transactions"
            ],
            dependencies=["mysql-connector-python>=8.0.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern via from_config() - one connection pool per application",
            "Connection pooling ensures efficient reuse of database connections",
            "Default pool size: minimum 1 connection, maximum 10 connections (configurable)",
            "All connections use autocommit=False for explicit transaction control",
            "Character set defaults to utf8mb4 for full Unicode support including emojis",
            "Connection pool automatically resets session state when connections are reused",
            "Parameterized queries with %s placeholders prevent SQL injection attacks",
            "execute_query() automatically commits for non-SELECT queries and rolls back on error",
            "execute_query_dict() returns results as list of dictionaries with column names as keys",
            "execute_many() provides batch execution for efficient bulk inserts and updates",
            "Connections are automatically returned to pool when released or closed",
            "Pool name is 'aibasic_mysql_pool' - visible in MySQL process list",
            "All methods raise RuntimeError on database errors with descriptive messages",
            "MySQL connector handles automatic reconnection for lost connections",
            "Stored procedures can be called with call_procedure() method",
            "Always use release_connection() or context managers to return connections to pool",
            "Query parameters must be passed as tuples, even for single parameter (param,)",
            "SELECT queries use fetch=True (default), INSERT/UPDATE/DELETE use fetch=False",
            "Transactions are manually controlled - use commit/rollback on connection object",
            "Pool status available via get_pool_status() for monitoring and debugging"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="get_connection",
                description="Get a database connection from the connection pool for manual query execution",
                parameters={},
                returns="mysql.connector.connection - Database connection object from pool",
                examples=[
                    {"text": "Get connection from pool", "code": "get_connection()"}
                ]
            ),
            MethodInfo(
                name="release_connection",
                description="Return a connection back to the pool for reuse by other operations",
                parameters={
                    "conn": "connection (required) - Connection object to return to pool"
                },
                returns="None",
                examples=[
                    {"text": "Release connection {{conn}} back to pool", "code": "release_connection(conn={{conn}})"}
                ]
            ),
            MethodInfo(
                name="execute_query",
                description="Execute SQL query with automatic connection handling, commits non-SELECT queries and fetches SELECT results",
                parameters={
                    "query": "str (required) - SQL query with %s placeholders for parameters",
                    "params": "tuple (optional) - Parameter values for placeholders",
                    "fetch": "bool (optional) - True to fetch results (SELECT), False for INSERT/UPDATE/DELETE (default True)"
                },
                returns="list[tuple] if fetch=True (SELECT results), None if fetch=False (INSERT/UPDATE/DELETE)",
                examples=[
                    {"text": "Select users older than {{age}}", "code": "execute_query(query='SELECT * FROM users WHERE age > %s', params=({{age}},))"},
                    {"text": "Insert user with name {{name}} and email {{email}}", "code": "execute_query(query='INSERT INTO users (name, email) VALUES (%s, %s)', params=({{name}}, {{email}}), fetch=False)"},
                    {"text": "Update user {{user_id}} with status {{status}}", "code": "execute_query(query='UPDATE users SET status = %s WHERE id = %s', params=({{status}}, {{user_id}}), fetch=False)"},
                    {"text": "Delete user {{user_id}}", "code": "execute_query(query='DELETE FROM users WHERE id = %s', params=({{user_id}},), fetch=False)"}
                ]
            ),
            MethodInfo(
                name="execute_query_dict",
                description="Execute SELECT query and return results as list of dictionaries with column names as keys",
                parameters={
                    "query": "str (required) - SQL SELECT query with %s placeholders",
                    "params": "tuple (optional) - Parameter values for placeholders"
                },
                returns="list[dict] - List of dictionaries, one per row with column names as keys",
                examples=[
                    {"text": "Select users older than {{age}} as dictionaries", "code": "execute_query_dict(query='SELECT id, name, email FROM users WHERE age > %s', params=({{age}},))"},
                    {"text": "Get products in category {{category}} as dictionaries", "code": "execute_query_dict(query='SELECT * FROM products WHERE category = %s', params=({{category}},))"},
                    {"text": "Get order totals grouped by name as dictionaries", "code": "execute_query_dict(query='SELECT name, SUM(amount) as total FROM orders GROUP BY name')"}
                ]
            ),
            MethodInfo(
                name="execute_many",
                description="Execute same SQL query multiple times with different parameters for efficient batch operations",
                parameters={
                    "query": "str (required) - SQL query with %s placeholders",
                    "params_list": "list[tuple] (required) - List of parameter tuples, one per execution"
                },
                returns="None - commits all operations or rolls back on error",
                examples=[
                    {"text": "Batch insert users from {{users_list}}", "code": "execute_many(query='INSERT INTO users (name, age) VALUES (%s, %s)', params_list={{users_list}})"},
                    {"text": "Batch insert products from {{products_list}}", "code": "execute_many(query='INSERT INTO products (sku, price) VALUES (%s, %s)', params_list={{products_list}})"},
                    {"text": "Batch update login times from {{login_updates}}", "code": "execute_many(query='UPDATE users SET last_login = %s WHERE id = %s', params_list={{login_updates}})"}
                ]
            ),
            MethodInfo(
                name="call_procedure",
                description="Call MySQL stored procedure with arguments and retrieve results",
                parameters={
                    "proc_name": "str (required) - Name of stored procedure to call",
                    "args": "tuple (optional) - Arguments to pass to procedure (default empty tuple)"
                },
                returns="list[any] or None - Results from procedure, None if no results",
                examples=[
                    {"text": "Call procedure get_user_orders with user_id {{user_id}}", "code": "call_procedure(proc_name='get_user_orders', args=({{user_id}},))"},
                    {"text": "Call procedure calculate_totals with year {{year}} and quarter {{quarter}}", "code": "call_procedure(proc_name='calculate_totals', args=({{year}}, {{quarter}}))"},
                    {"text": "Call procedure cleanup_old_data", "code": "call_procedure(proc_name='cleanup_old_data')"}
                ]
            ),
            MethodInfo(
                name="get_pool_status",
                description="Get connection pool configuration and status information for monitoring",
                parameters={},
                returns="dict - Dictionary with host, port, database, charset, min/max connections, pool name",
                examples=[
                    {"text": "Get connection pool status", "code": "get_pool_status()"}
                ]
            ),
            MethodInfo(
                name="close_all_connections",
                description="Close all connections in the pool (called automatically on program termination)",
                parameters={},
                returns="None - prints cleanup confirmation",
                examples=[
                    {"text": "Close all connections in pool", "code": "close_all_connections()"}
                ]
            )
        ]

