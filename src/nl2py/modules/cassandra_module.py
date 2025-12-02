"""
Apache Cassandra Module for Distributed NoSQL Database

This module provides connection management and operations for Apache Cassandra,
a highly scalable, distributed NoSQL database.
Configuration is loaded from nl2py.conf under the [cassandra] section.

Supports:
- Multiple contact points (cluster nodes)
- Consistency levels (ONE, QUORUM, ALL, etc.)
- SSL/TLS encryption with certificate verification
- Authentication (username/password)
- Load balancing policies
- Retry policies
- Connection pooling
- Prepared statements for performance
- Batch operations
- Asynchronous queries
- Time-series data operations
- Counter columns
- Collections (lists, sets, maps)

Features:
- Execute CQL (Cassandra Query Language) queries
- Prepared statements with parameter binding
- Batch operations for atomic writes
- Paging for large result sets
- TTL (Time To Live) for automatic data expiration
- Lightweight transactions (Compare-And-Set)
- User-defined types (UDT)
- Secondary indexes

Example configuration in nl2py.conf:
    [cassandra]
    CONTACT_POINTS=localhost,192.168.1.100,192.168.1.101
    PORT=9042
    KEYSPACE=my_keyspace
    USERNAME=cassandra
    PASSWORD=cassandra

    # SSL/TLS Settings
    USE_SSL=false
    SSL_VERIFY=true
    SSL_CA_CERT=/path/to/ca.pem
    SSL_CLIENT_CERT=/path/to/client-cert.pem
    SSL_CLIENT_KEY=/path/to/client-key.pem

    # Connection Settings
    CONSISTENCY_LEVEL=LOCAL_QUORUM
    LOAD_BALANCING_POLICY=RoundRobinPolicy
    PROTOCOL_VERSION=4
    CONNECT_TIMEOUT=10
    REQUEST_TIMEOUT=30

Usage in generated code:
    from nl2py.modules import CassandraModule

    # Initialize module
    cass = CassandraModule.from_config('nl2py.conf')

    # Execute queries
    cass.execute("INSERT INTO users (id, name, email) VALUES (uuid(), 'Alice', 'alice@example.com')")
    rows = cass.execute("SELECT * FROM users WHERE id = ?", [user_id])

    # Prepared statements (better performance)
    cass.execute_prepared("SELECT * FROM users WHERE email = ?", ['alice@example.com'])

    # Batch operations
    cass.execute_batch([
        "INSERT INTO users (id, name) VALUES (uuid(), 'Bob')",
        "UPDATE users SET last_login = toTimestamp(now()) WHERE id = ?"
    ])

    # Create keyspace and tables
    cass.create_keyspace('my_app', replication_factor=3)
    cass.create_table('users', {'id': 'uuid', 'name': 'text', 'email': 'text'}, 'id')
"""

import configparser
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from uuid import UUID

try:
    from cassandra.cluster import Cluster, Session, ExecutionProfile, EXEC_PROFILE_DEFAULT
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.policies import (
        RoundRobinPolicy, DCAwareRoundRobinPolicy, TokenAwarePolicy,
        RetryPolicy, DowngradingConsistencyRetryPolicy
    )
    from cassandra.query import SimpleStatement, PreparedStatement, BatchStatement, ConsistencyLevel
    from cassandra import ConsistencyLevel as CL
    import ssl as ssl_module
except ImportError:
    Cluster = None
    Session = None
    PlainTextAuthProvider = None
    CL = None


from .module_base import NL2PyModuleBase


class CassandraModule(NL2PyModuleBase):
    """
    Apache Cassandra distributed NoSQL database module.

    Supports clustering, consistency levels, SSL/TLS, and advanced features.
    """

    _instance = None
    _lock = threading.Lock()

    # Consistency level mapping
    CONSISTENCY_LEVELS = {
        'ANY': 'ANY',
        'ONE': 'ONE',
        'TWO': 'TWO',
        'THREE': 'THREE',
        'QUORUM': 'QUORUM',
        'ALL': 'ALL',
        'LOCAL_QUORUM': 'LOCAL_QUORUM',
        'EACH_QUORUM': 'EACH_QUORUM',
        'LOCAL_ONE': 'LOCAL_ONE'
    }

    def __init__(
        self,
        contact_points: List[str] = None,
        port: int = 9042,
        keyspace: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False,
        ssl_verify: bool = True,
        ssl_ca_cert: Optional[str] = None,
        ssl_client_cert: Optional[str] = None,
        ssl_client_key: Optional[str] = None,
        consistency_level: str = 'LOCAL_QUORUM',
        load_balancing_policy: str = 'RoundRobinPolicy',
        protocol_version: int = 4,
        connect_timeout: int = 10,
        request_timeout: int = 30
    ):
        """
        Initialize the CassandraModule.

        Args:
            contact_points: List of cluster node addresses
            port: Cassandra port (default 9042)
            keyspace: Default keyspace to use
            username: Authentication username
            password: Authentication password
            use_ssl: Enable SSL/TLS connection
            ssl_verify: Verify SSL certificates
            ssl_ca_cert: Path to CA certificate
            ssl_client_cert: Path to client certificate
            ssl_client_key: Path to client key
            consistency_level: Default consistency level
            load_balancing_policy: Load balancing strategy
            protocol_version: CQL protocol version
            connect_timeout: Connection timeout in seconds
            request_timeout: Request timeout in seconds
        """
        if Cluster is None:
            raise ImportError(
                "cassandra-driver is required. Install with: pip install cassandra-driver"
            )

        self.contact_points = contact_points or ['localhost']
        self.port = port
        self.keyspace = keyspace
        self.default_consistency = getattr(CL, consistency_level)

        # Authentication
        auth_provider = None
        if username and password:
            auth_provider = PlainTextAuthProvider(username=username, password=password)
            print(f"[CassandraModule] Using authentication as {username}")

        # Load balancing policy
        if load_balancing_policy == 'RoundRobinPolicy':
            lb_policy = RoundRobinPolicy()
        elif load_balancing_policy == 'DCAwareRoundRobinPolicy':
            lb_policy = DCAwareRoundRobinPolicy()
        elif load_balancing_policy == 'TokenAwarePolicy':
            lb_policy = TokenAwarePolicy(RoundRobinPolicy())
        else:
            lb_policy = RoundRobinPolicy()

        # SSL/TLS configuration
        ssl_options = None
        if use_ssl:
            ssl_context = ssl_module.create_default_context()

            if not ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl_module.CERT_NONE
                print("[CassandraModule] ⚠️  SSL certificate verification DISABLED")
            else:
                if ssl_ca_cert:
                    ssl_context.load_verify_locations(ssl_ca_cert)

            if ssl_client_cert and ssl_client_key:
                ssl_context.load_cert_chain(ssl_client_cert, ssl_client_key)

            ssl_options = {'ssl_context': ssl_context}

        # Create cluster
        self.cluster = Cluster(
            contact_points=self.contact_points,
            port=port,
            auth_provider=auth_provider,
            load_balancing_policy=lb_policy,
            protocol_version=protocol_version,
            ssl_options=ssl_options,
            connect_timeout=connect_timeout,
            control_connection_timeout=connect_timeout
        )

        # Create session
        if keyspace:
            self.session = self.cluster.connect(keyspace)
            print(f"[CassandraModule] Connected to Cassandra cluster, using keyspace '{keyspace}'")
        else:
            self.session = self.cluster.connect()
            print("[CassandraModule] Connected to Cassandra cluster, no default keyspace")

        # Set default timeout
        self.session.default_timeout = request_timeout

        # Prepared statement cache
        self._prepared_statements = {}

        # Print cluster info
        metadata = self.cluster.metadata
        print(f"[CassandraModule] Cluster name: {metadata.cluster_name}")
        print(f"[CassandraModule] Available hosts: {len(metadata.all_hosts())}")

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf") -> 'CassandraModule':
        """
        Create a CassandraModule from configuration file.
        Uses singleton pattern to ensure only one instance exists.

        Args:
            config_path: Path to nl2py.conf file

        Returns:
            CassandraModule instance
        """
        with cls._lock:
            if cls._instance is None:
                config = configparser.ConfigParser()
                path = Path(config_path)

                if not path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_path}")

                config.read(path)

                if 'cassandra' not in config:
                    raise KeyError("Missing [cassandra] section in nl2py.conf")

                cass_config = config['cassandra']

                # Connection
                contact_points_str = cass_config.get('CONTACT_POINTS', 'localhost')
                contact_points = [cp.strip() for cp in contact_points_str.split(',')]
                port = cass_config.getint('PORT', 9042)
                keyspace = cass_config.get('KEYSPACE', None)

                # Authentication
                username = cass_config.get('USERNAME', None)
                password = cass_config.get('PASSWORD', None)

                # SSL/TLS
                use_ssl = cass_config.getboolean('USE_SSL', False)
                ssl_verify = cass_config.getboolean('SSL_VERIFY', True)
                ssl_ca_cert = cass_config.get('SSL_CA_CERT', None)
                ssl_client_cert = cass_config.get('SSL_CLIENT_CERT', None)
                ssl_client_key = cass_config.get('SSL_CLIENT_KEY', None)

                # Settings
                consistency_level = cass_config.get('CONSISTENCY_LEVEL', 'LOCAL_QUORUM')
                load_balancing_policy = cass_config.get('LOAD_BALANCING_POLICY', 'RoundRobinPolicy')
                protocol_version = cass_config.getint('PROTOCOL_VERSION', 4)
                connect_timeout = cass_config.getint('CONNECT_TIMEOUT', 10)
                request_timeout = cass_config.getint('REQUEST_TIMEOUT', 30)

                cls._instance = cls(
                    contact_points=contact_points,
                    port=port,
                    keyspace=keyspace,
                    username=username,
                    password=password,
                    use_ssl=use_ssl,
                    ssl_verify=ssl_verify,
                    ssl_ca_cert=ssl_ca_cert,
                    ssl_client_cert=ssl_client_cert,
                    ssl_client_key=ssl_client_key,
                    consistency_level=consistency_level,
                    load_balancing_policy=load_balancing_policy,
                    protocol_version=protocol_version,
                    connect_timeout=connect_timeout,
                    request_timeout=request_timeout
                )

            return cls._instance

    # ==================== Query Execution ====================

    def execute(
        self,
        query: str,
        parameters: Optional[Union[List, Tuple, Dict]] = None,
        consistency_level: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> List[Any]:
        """
        Execute a CQL query.

        Args:
            query: CQL query string
            parameters: Query parameters (list, tuple, or dict for named params)
            consistency_level: Override default consistency level
            timeout: Query timeout in seconds

        Returns:
            List of Row objects
        """
        statement = SimpleStatement(query)

        if consistency_level:
            statement.consistency_level = getattr(CL, consistency_level)
        else:
            statement.consistency_level = self.default_consistency

        result = self.session.execute(statement, parameters, timeout=timeout)
        return list(result)

    def execute_async(
        self,
        query: str,
        parameters: Optional[Union[List, Tuple, Dict]] = None,
        consistency_level: Optional[str] = None
    ):
        """
        Execute a CQL query asynchronously.

        Returns:
            ResponseFuture object
        """
        statement = SimpleStatement(query)

        if consistency_level:
            statement.consistency_level = getattr(CL, consistency_level)
        else:
            statement.consistency_level = self.default_consistency

        return self.session.execute_async(statement, parameters)

    def execute_prepared(
        self,
        query: str,
        parameters: Union[List, Tuple, Dict],
        consistency_level: Optional[str] = None
    ) -> List[Any]:
        """
        Execute a prepared statement (cached for performance).

        Args:
            query: CQL query string
            parameters: Query parameters
            consistency_level: Override default consistency level

        Returns:
            List of Row objects
        """
        # Cache prepared statements
        if query not in self._prepared_statements:
            self._prepared_statements[query] = self.session.prepare(query)

        prepared = self._prepared_statements[query]

        if consistency_level:
            prepared.consistency_level = getattr(CL, consistency_level)
        else:
            prepared.consistency_level = self.default_consistency

        result = self.session.execute(prepared, parameters)
        return list(result)

    def execute_batch(
        self,
        statements: List[Union[str, Tuple[str, List]]],
        consistency_level: Optional[str] = None,
        batch_type: str = 'LOGGED'
    ) -> None:
        """
        Execute multiple statements in a batch (atomic).

        Args:
            statements: List of CQL statements or (statement, parameters) tuples
            consistency_level: Consistency level for batch
            batch_type: LOGGED, UNLOGGED, or COUNTER
        """
        from cassandra.query import BatchType

        batch_type_map = {
            'LOGGED': BatchType.LOGGED,
            'UNLOGGED': BatchType.UNLOGGED,
            'COUNTER': BatchType.COUNTER
        }

        batch = BatchStatement(batch_type=batch_type_map.get(batch_type, BatchType.LOGGED))

        if consistency_level:
            batch.consistency_level = getattr(CL, consistency_level)
        else:
            batch.consistency_level = self.default_consistency

        for stmt in statements:
            if isinstance(stmt, tuple):
                query, params = stmt
                batch.add(SimpleStatement(query), params)
            else:
                batch.add(SimpleStatement(stmt))

        self.session.execute(batch)
        print(f"[CassandraModule] Executed batch with {len(statements)} statements")

    # ==================== Keyspace Operations ====================

    def create_keyspace(
        self,
        keyspace: str,
        replication_strategy: str = 'SimpleStrategy',
        replication_factor: int = 1,
        durable_writes: bool = True
    ) -> None:
        """
        Create a keyspace.

        Args:
            keyspace: Keyspace name
            replication_strategy: SimpleStrategy or NetworkTopologyStrategy
            replication_factor: Number of replicas
            durable_writes: Enable durable writes
        """
        if replication_strategy == 'SimpleStrategy':
            replication = f"{{'class': 'SimpleStrategy', 'replication_factor': {replication_factor}}}"
        else:
            replication = f"{{'class': '{replication_strategy}', 'replication_factor': {replication_factor}}}"

        query = f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {replication}
            AND durable_writes = {str(durable_writes).lower()}
        """

        self.execute(query)
        print(f"[CassandraModule] Keyspace '{keyspace}' created")

    def drop_keyspace(self, keyspace: str) -> None:
        """Drop a keyspace."""
        self.execute(f"DROP KEYSPACE IF EXISTS {keyspace}")
        print(f"[CassandraModule] Keyspace '{keyspace}' dropped")

    def use_keyspace(self, keyspace: str) -> None:
        """Switch to a different keyspace."""
        self.session.set_keyspace(keyspace)
        self.keyspace = keyspace
        print(f"[CassandraModule] Switched to keyspace '{keyspace}'")

    def list_keyspaces(self) -> List[str]:
        """List all keyspaces."""
        return [ks.name for ks in self.cluster.metadata.keyspaces.values()]

    # ==================== Table Operations ====================

    def create_table(
        self,
        table: str,
        columns: Dict[str, str],
        primary_key: Union[str, List[str]],
        clustering_order: Optional[Dict[str, str]] = None,
        compact_storage: bool = False
    ) -> None:
        """
        Create a table.

        Args:
            table: Table name
            columns: Dict of {column_name: type}
            primary_key: Single column or list of columns for partition/clustering key
            clustering_order: Dict of {column: 'ASC' or 'DESC'}
            compact_storage: Enable compact storage (deprecated)
        """
        cols_def = ", ".join([f"{col} {typ}" for col, typ in columns.items()])

        if isinstance(primary_key, list):
            pk = f"({', '.join(primary_key)})"
        else:
            pk = primary_key

        query = f"CREATE TABLE IF NOT EXISTS {table} ({cols_def}, PRIMARY KEY ({pk}))"

        if clustering_order:
            order_clause = ", ".join([f"{col} {order}" for col, order in clustering_order.items()])
            query += f" WITH CLUSTERING ORDER BY ({order_clause})"

        if compact_storage:
            query += " AND COMPACT STORAGE"

        self.execute(query)
        print(f"[CassandraModule] Table '{table}' created")

    def drop_table(self, table: str) -> None:
        """Drop a table."""
        self.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"[CassandraModule] Table '{table}' dropped")

    def truncate_table(self, table: str) -> None:
        """Truncate a table (remove all rows)."""
        self.execute(f"TRUNCATE TABLE {table}")
        print(f"[CassandraModule] Table '{table}' truncated")

    def list_tables(self, keyspace: Optional[str] = None) -> List[str]:
        """List all tables in a keyspace."""
        ks = keyspace or self.keyspace
        if ks:
            metadata = self.cluster.metadata.keyspaces.get(ks)
            if metadata:
                return list(metadata.tables.keys())
        return []

    # ==================== CRUD Operations ====================

    def insert(
        self,
        table: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        if_not_exists: bool = False
    ) -> None:
        """
        Insert a row.

        Args:
            table: Table name
            data: Dict of {column: value}
            ttl: Time to live in seconds
            if_not_exists: Use IF NOT EXISTS (lightweight transaction)
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        values = list(data.values())

        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        if ttl:
            query += f" USING TTL {ttl}"

        if if_not_exists:
            query += " IF NOT EXISTS"

        self.execute(query, values)

    def select(
        self,
        table: str,
        columns: Union[str, List[str]] = '*',
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        allow_filtering: bool = False
    ) -> List[Any]:
        """
        Select rows from a table.

        Args:
            table: Table name
            columns: Column(s) to select
            where: WHERE clause dict {column: value}
            limit: Maximum rows to return
            allow_filtering: Allow filtering (use carefully)

        Returns:
            List of Row objects
        """
        if isinstance(columns, list):
            cols = ", ".join(columns)
        else:
            cols = columns

        query = f"SELECT {cols} FROM {table}"

        params = []
        if where:
            where_clauses = [f"{col} = ?" for col in where.keys()]
            query += " WHERE " + " AND ".join(where_clauses)
            params = list(where.values())

        if limit:
            query += f" LIMIT {limit}"

        if allow_filtering:
            query += " ALLOW FILTERING"

        return self.execute(query, params if params else None)

    def update(
        self,
        table: str,
        set_values: Dict[str, Any],
        where: Dict[str, Any],
        ttl: Optional[int] = None,
        if_exists: bool = False
    ) -> None:
        """
        Update rows.

        Args:
            table: Table name
            set_values: Dict of {column: new_value}
            where: WHERE clause dict
            ttl: Time to live in seconds
            if_exists: Use IF EXISTS (lightweight transaction)
        """
        set_clauses = [f"{col} = ?" for col in set_values.keys()]
        where_clauses = [f"{col} = ?" for col in where.keys()]

        query = f"UPDATE {table}"

        if ttl:
            query += f" USING TTL {ttl}"

        query += " SET " + ", ".join(set_clauses)
        query += " WHERE " + " AND ".join(where_clauses)

        if if_exists:
            query += " IF EXISTS"

        params = list(set_values.values()) + list(where.values())
        self.execute(query, params)

    def delete(
        self,
        table: str,
        where: Dict[str, Any],
        columns: Optional[List[str]] = None,
        if_exists: bool = False
    ) -> None:
        """
        Delete rows or specific columns.

        Args:
            table: Table name
            where: WHERE clause dict
            columns: Specific columns to delete (None = entire row)
            if_exists: Use IF EXISTS
        """
        if columns:
            cols = ", ".join(columns)
            query = f"DELETE {cols} FROM {table}"
        else:
            query = f"DELETE FROM {table}"

        where_clauses = [f"{col} = ?" for col in where.keys()]
        query += " WHERE " + " AND ".join(where_clauses)

        if if_exists:
            query += " IF EXISTS"

        params = list(where.values())
        self.execute(query, params)

    # ==================== Counter Operations ====================

    def increment_counter(self, table: str, counter_col: str, where: Dict[str, Any], amount: int = 1) -> None:
        """Increment a counter column."""
        where_clauses = [f"{col} = ?" for col in where.keys()]
        query = f"UPDATE {table} SET {counter_col} = {counter_col} + ? WHERE " + " AND ".join(where_clauses)
        params = [amount] + list(where.values())
        self.execute(query, params)

    def decrement_counter(self, table: str, counter_col: str, where: Dict[str, Any], amount: int = 1) -> None:
        """Decrement a counter column."""
        where_clauses = [f"{col} = ?" for col in where.keys()]
        query = f"UPDATE {table} SET {counter_col} = {counter_col} - ? WHERE " + " AND ".join(where_clauses)
        params = [amount] + list(where.values())
        self.execute(query, params)

    # ==================== Utility Operations ====================

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information."""
        metadata = self.cluster.metadata
        return {
            'cluster_name': metadata.cluster_name,
            'all_hosts': [str(host.address) for host in metadata.all_hosts()],
            'keyspaces': list(metadata.keyspaces.keys()),
            'protocol_version': self.cluster.protocol_version
        }

    def close(self):
        """Close connection."""
        if self.session:
            self.session.shutdown()
        if self.cluster:
            self.cluster.shutdown()
        print("[CassandraModule] Connection closed")

    def __del__(self):
        """Destructor to ensure connection is closed."""
        try:
            self.close()
        except:
            pass

    # =============================================================================
    # Metadata Methods for NL2Py Compiler
    # =============================================================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Cassandra",
            task_type="cassandra",
            description="Apache Cassandra distributed NoSQL database with support for clustering, consistency levels, and CQL queries",
            version="1.0.0",
            keywords=["cassandra", "nosql", "distributed", "database", "cql", "cluster", "keyspace", "timeseries", "wide-column"],
            dependencies=["cassandra-driver>=3.25.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes."""
        return [
            "Module uses singleton pattern via from_config() - one instance per application",
            "Supports distributed cluster with multiple contact points for high availability",
            "Consistency levels: ANY, ONE, TWO, THREE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM, LOCAL_ONE",
            "Default consistency level is LOCAL_QUORUM (balance between performance and consistency)",
            "Prepared statements are automatically cached for better performance on repeated queries",
            "Batch operations provide atomicity for multiple writes within same partition",
            "TTL (Time To Live) can be set on insert/update for automatic data expiration",
            "Lightweight transactions (IF NOT EXISTS, IF EXISTS) ensure atomic operations but have performance cost",
            "ALLOW FILTERING enables queries on non-primary-key columns (use carefully, impacts performance)",
            "Keyspaces provide namespace isolation, similar to databases in SQL systems",
            "Tables use partition keys for data distribution and clustering keys for ordering",
            "Counter columns support atomic increment/decrement operations",
            "SSL/TLS support for encrypted connections with certificate verification",
            "Authentication via username/password (PlainTextAuthProvider)",
            "Load balancing policies: RoundRobinPolicy, DCAwareRoundRobinPolicy, TokenAwarePolicy",
            "Asynchronous query execution available via execute_async()",
            "Connection pooling and retry policies handled automatically by driver",
            "Key methods: execute, execute_prepared, execute_batch, insert, select, update, delete, create_keyspace, create_table",
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about module methods."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="from_config",
                description="Create CassandraModule instance from nl2py.conf file (singleton pattern)",
                parameters={
                    "config_path": "Path to nl2py.conf (default: 'nl2py.conf')"
                },
                returns="CassandraModule instance configured with settings from [cassandra] section",
                examples=[
                    {"text": "Initialize from configuration file {{nl2py.conf}}", "code": "from_config(config_path='{{nl2py.conf}}')"},
                    {"text": "Connect using default config", "code": "from_config()"},
                ]
            ),
            MethodInfo(
                name="execute",
                description="Execute a CQL query with optional parameters and consistency level",
                parameters={
                    "query": "CQL query string with ? placeholders for parameters",
                    "parameters": "List, tuple, or dict of parameter values (optional)",
                    "consistency_level": "Override default consistency (optional: ONE, QUORUM, ALL, etc.)",
                    "timeout": "Query timeout in seconds (optional)"
                },
                returns="List of Row objects containing query results",
                examples=[
                    {"text": "Execute CQL query {{SELECT * FROM users WHERE id = ?}} with parameters {{user_id}}", "code": "execute(query='{{SELECT * FROM users WHERE id = ?}}', parameters=[{{user_id}}])"},
                    {"text": "Insert data {{INSERT INTO logs (timestamp, message) VALUES (?, ?)}} with parameters {{timestamp}}, {{message}}", "code": "execute(query='{{INSERT INTO logs (timestamp, message) VALUES (?, ?)}}', parameters=[{{timestamp}}, {{message}}])"},
                    {"text": "Execute query {{SELECT * FROM events}} with consistency level {{ONE}}", "code": "execute(query='{{SELECT * FROM events}}', consistency_level='{{ONE}}')"},
                ]
            ),
            MethodInfo(
                name="execute_prepared",
                description="Execute a prepared statement (cached for performance on repeated queries)",
                parameters={
                    "query": "CQL query string (will be prepared and cached)",
                    "parameters": "List, tuple, or dict of parameter values",
                    "consistency_level": "Override default consistency (optional)"
                },
                returns="List of Row objects containing query results",
                examples=[
                    {"text": "Execute prepared statement {{SELECT * FROM users WHERE email = ?}} with parameters {{user@example.com}}", "code": "execute_prepared(query='{{SELECT * FROM users WHERE email = ?}}', parameters=[{{user@example.com}}])"},
                    {"text": "Run prepared update statement {{UPDATE users SET last_login = ? WHERE id = ?}} with parameters {{timestamp}}, {{user_id}}", "code": "execute_prepared(query='{{UPDATE users SET last_login = ? WHERE id = ?}}', parameters=[{{timestamp}}, {{user_id}}])"},
                ]
            ),
            MethodInfo(
                name="execute_batch",
                description="Execute multiple CQL statements atomically within a batch",
                parameters={
                    "statements": "List of CQL strings or (query, parameters) tuples",
                    "consistency_level": "Consistency level for the batch (optional)",
                    "batch_type": "LOGGED (default, atomic), UNLOGGED (faster), or COUNTER"
                },
                returns="None - raises exception on failure",
                examples=[
                    {"text": "Execute batch of statements {{INSERT INTO users VALUES (?, ?)}}, {{UPDATE stats SET count = count + 1}}", "code": "execute_batch(statements=[{{INSERT INTO users VALUES (?, ?)}}, {{UPDATE stats SET count = count + 1}}])"},
                    {"text": "Run batch with statements {{stmt1}}, {{stmt2}}, batch type {{LOGGED}}, consistency level {{QUORUM}}", "code": "execute_batch(statements=[{{stmt1}}, {{stmt2}}], batch_type='{{LOGGED}}', consistency_level='{{QUORUM}}')"},
                ]
            ),
            MethodInfo(
                name="create_keyspace",
                description="Create a keyspace (namespace for tables)",
                parameters={
                    "keyspace": "Keyspace name (string)",
                    "replication_strategy": "SimpleStrategy (default) or NetworkTopologyStrategy",
                    "replication_factor": "Number of replicas (default: 1, production: 3+)",
                    "durable_writes": "Enable durable writes (default: True)"
                },
                returns="None - creates keyspace if it doesn't exist",
                examples=[
                    {"text": "Create keyspace {{my_app}} with replication factor {{3}}", "code": "create_keyspace(keyspace='{{my_app}}', replication_factor={{3}})"},
                    {"text": "Create keyspace {{prod_data}} with strategy {{SimpleStrategy}} and replication factor {{3}}", "code": "create_keyspace(keyspace='{{prod_data}}', replication_strategy='{{SimpleStrategy}}', replication_factor={{3}})"},
                ]
            ),
            MethodInfo(
                name="create_table",
                description="Create a table with columns and primary key definition",
                parameters={
                    "table": "Table name (string)",
                    "columns": "Dict of {column_name: cassandra_type} (e.g., {'id': 'uuid', 'name': 'text'})",
                    "primary_key": "Single column name or list [partition_key, clustering_key, ...]",
                    "clustering_order": "Dict of {column: 'ASC' or 'DESC'} for clustering columns (optional)",
                    "compact_storage": "Enable compact storage - deprecated (default: False)"
                },
                returns="None - creates table if it doesn't exist",
                examples=[
                    {"text": "Create simple table {{users}} with columns {{id}}, {{name}}, {{email}} and primary key {{id}}", "code": "create_table(table='{{users}}', columns={'{{id}}': '{{uuid}}', '{{name}}': '{{text}}', '{{email}}': '{{text}}'}, primary_key='{{id}}')"},
                    {"text": "Create table {{events}} with columns {{user_id}}, {{timestamp}}, {{event}} and composite primary key {{user_id}}, {{timestamp}}", "code": "create_table(table='{{events}}', columns={'{{user_id}}': '{{uuid}}', '{{timestamp}}': '{{timestamp}}', '{{event}}': '{{text}}'}, primary_key=['{{user_id}}', '{{timestamp}}'])"},
                ]
            ),
            MethodInfo(
                name="insert",
                description="Insert a row into a table with optional TTL and conditional logic",
                parameters={
                    "table": "Table name (string)",
                    "data": "Dict of {column: value} to insert",
                    "ttl": "Time to live in seconds for automatic expiration (optional)",
                    "if_not_exists": "Use lightweight transaction to ensure row doesn't exist (default: False)"
                },
                returns="None - inserts row or raises exception on error",
                examples=[
                    {"text": "Insert data into table {{users}} with {{id}}, {{name}}, {{email}}", "code": "insert(table='{{users}}', data={'{{id}}': '{{uuid()}}', '{{name}}': '{{Alice}}', '{{email}}': '{{alice@example.com}}'})"},
                    {"text": "Insert into table {{sessions}} with data {{session_id}}, {{user}} and TTL {{3600}}", "code": "insert(table='{{sessions}}', data={'{{session_id}}': '{{abc123}}', '{{user}}': '{{alice}}'}, ttl={{3600}})"},
                    {"text": "Insert into table {{locks}} with data {{resource}}, {{owner}} only if not exists", "code": "insert(table='{{locks}}', data={'{{resource}}': '{{db}}', '{{owner}}': '{{worker1}}'}, if_not_exists={{True}})"},
                ]
            ),
            MethodInfo(
                name="select",
                description="Select rows from a table with optional filtering and limits",
                parameters={
                    "table": "Table name (string)",
                    "columns": "Single column, list of columns, or '*' for all (default: '*')",
                    "where": "Dict of {column: value} for WHERE clause (optional)",
                    "limit": "Maximum number of rows to return (optional)",
                    "allow_filtering": "Enable filtering on non-primary-key columns (use carefully, default: False)"
                },
                returns="List of Row objects with results",
                examples=[
                    {"text": "Select rows from table {{users}} by primary key {{id}} = {{user_id}}", "code": "select(table='{{users}}', where={'{{id}}': {{user_id}}})"},
                    {"text": "Select columns {{name}}, {{email}} from table {{users}} where {{id}} = {{user_id}}", "code": "select(table='{{users}}', columns=['{{name}}', '{{email}}'], where={'{{id}}': {{user_id}}})"},
                    {"text": "Select from table {{events}} where {{user_id}} = {{uid}} with limit {{100}}", "code": "select(table='{{events}}', where={'{{user_id}}': {{uid}}}, limit={{100}})"},
                    {"text": "Select from table {{users}} where {{status}} = {{active}} with filtering", "code": "select(table='{{users}}', where={'{{status}}': '{{active}}'}, allow_filtering={{True}})"},
                ]
            ),
            MethodInfo(
                name="update",
                description="Update rows in a table with optional TTL and conditional logic",
                parameters={
                    "table": "Table name (string)",
                    "set_values": "Dict of {column: new_value} to update",
                    "where": "Dict of {column: value} for WHERE clause (required for primary key)",
                    "ttl": "Time to live in seconds (optional)",
                    "if_exists": "Use lightweight transaction to ensure row exists (default: False)"
                },
                returns="None - updates row(s) or raises exception on error",
                examples=[
                    {"text": "Update table {{users}} set {{last_login}} where {{id}} = {{user_id}}", "code": "update(table='{{users}}', set_values={'{{last_login}}': {{now()}}}, where={'{{id}}': {{user_id}}})"},
                    {"text": "Update table {{sessions}} set {{data}} where {{session_id}} = {{abc123}} with TTL {{1800}}", "code": "update(table='{{sessions}}', set_values={'{{data}}': {{session_data}}}, where={'{{session_id}}': '{{abc123}}'}, ttl={{1800}})"},
                    {"text": "Update table {{users}} set {{name}} = {{Bob}} where {{id}} = {{user_id}} only if exists", "code": "update(table='{{users}}', set_values={'{{name}}': '{{Bob}}'}, where={'{{id}}': {{user_id}}}, if_exists={{True}})"},
                ]
            ),
            MethodInfo(
                name="delete",
                description="Delete rows or specific columns from a table",
                parameters={
                    "table": "Table name (string)",
                    "where": "Dict of {column: value} for WHERE clause (required)",
                    "columns": "List of specific columns to delete (optional: None = entire row)",
                    "if_exists": "Use lightweight transaction (default: False)"
                },
                returns="None - deletes row(s) or raises exception on error",
                examples=[
                    {"text": "Delete entire row from table {{users}} where {{id}} = {{user_id}}", "code": "delete(table='{{users}}', where={'{{id}}': {{user_id}}})"},
                    {"text": "Delete columns {{email}}, {{phone}} from table {{users}} where {{id}} = {{user_id}}", "code": "delete(table='{{users}}', where={'{{id}}': {{user_id}}}, columns=['{{email}}', '{{phone}}'])"},
                    {"text": "Delete from table {{sessions}} where {{session_id}} = {{abc123}} only if exists", "code": "delete(table='{{sessions}}', where={'{{session_id}}': '{{abc123}}'}, if_exists={{True}})"},
                ]
            ),
            MethodInfo(
                name="increment_counter",
                description="Atomically increment a counter column (requires counter table)",
                parameters={
                    "table": "Counter table name (string)",
                    "counter_col": "Counter column name to increment",
                    "where": "Dict of {column: value} for WHERE clause (primary key)",
                    "amount": "Amount to increment by (default: 1)"
                },
                returns="None - increments counter atomically",
                examples=[
                    {"text": "Increment counter {{page_views}} in table {{stats}} where {{page_id}} = {{home}}", "code": "increment_counter(table='{{stats}}', counter_col='{{page_views}}', where={'{{page_id}}': '{{home}}'})"},
                    {"text": "Increment counter {{count}} in table {{metrics}} where {{metric_name}} = {{requests}} by amount {{10}}", "code": "increment_counter(table='{{metrics}}', counter_col='{{count}}', where={'{{metric_name}}': '{{requests}}'}, amount={{10}})"},
                ]
            ),
            MethodInfo(
                name="decrement_counter",
                description="Atomically decrement a counter column (requires counter table)",
                parameters={
                    "table": "Counter table name (string)",
                    "counter_col": "Counter column name to decrement",
                    "where": "Dict of {column: value} for WHERE clause (primary key)",
                    "amount": "Amount to decrement by (default: 1)"
                },
                returns="None - decrements counter atomically",
                examples=[
                    {"text": "Decrement counter {{inventory}} in table {{products}} where {{product_id}} = {{SKU123}}", "code": "decrement_counter(table='{{products}}', counter_col='{{inventory}}', where={'{{product_id}}': '{{SKU123}}'})"},
                    {"text": "Decrement counter {{quota}} in table {{users}} where {{user_id}} = {{user_id}} by amount {{5}}", "code": "decrement_counter(table='{{users}}', counter_col='{{quota}}', where={'{{user_id}}': {{user_id}}}, amount={{5}})"},
                ]
            ),
            MethodInfo(
                name="list_keyspaces",
                description="List all keyspaces in the Cassandra cluster",
                parameters={},
                returns="List of keyspace names (strings)",
                examples=[
                    {"text": "List all keyspaces", "code": "list_keyspaces()"},
                    {"text": "Get all keyspaces in cluster", "code": "list_keyspaces()"},
                ]
            ),
            MethodInfo(
                name="list_tables",
                description="List all tables in a keyspace",
                parameters={
                    "keyspace": "Keyspace name (optional: uses current keyspace if not specified)"
                },
                returns="List of table names (strings)",
                examples=[
                    {"text": "List tables in keyspace {{my_app}}", "code": "list_tables(keyspace='{{my_app}}')"},
                    {"text": "List tables in current keyspace", "code": "list_tables()"},
                ]
            ),
            MethodInfo(
                name="drop_keyspace",
                description="Drop a keyspace and all its tables (destructive operation)",
                parameters={"keyspace": "Keyspace name to drop (string)"},
                returns="None - drops keyspace if exists",
                examples=[
                    {"text": "Drop keyspace {{old_app}}", "code": "drop_keyspace(keyspace='{{old_app}}')"},
                    {"text": "Delete keyspace {{test_data}} and all its tables", "code": "drop_keyspace(keyspace='{{test_data}}')"},
                ]
            ),
            MethodInfo(
                name="use_keyspace",
                description="Switch to a different keyspace for subsequent operations",
                parameters={"keyspace": "Keyspace name to switch to (string)"},
                returns="None - changes current keyspace context",
                examples=[
                    {"text": "Switch to keyspace {{production}}", "code": "use_keyspace(keyspace='{{production}}')"},
                    {"text": "Change current keyspace context to {{analytics}}", "code": "use_keyspace(keyspace='{{analytics}}')"},
                ]
            ),
            MethodInfo(
                name="drop_table",
                description="Drop a table from the current keyspace (destructive operation)",
                parameters={"table": "Table name to drop (string)"},
                returns="None - drops table if exists",
                examples=[
                    {"text": "Drop table {{old_logs}}", "code": "drop_table(table='{{old_logs}}')"},
                    {"text": "Delete table {{temp_data}} from keyspace", "code": "drop_table(table='{{temp_data}}')"},
                ]
            ),
            MethodInfo(
                name="truncate_table",
                description="Remove all rows from a table while keeping the schema",
                parameters={"table": "Table name to truncate (string)"},
                returns="None - removes all data from table",
                examples=[
                    {"text": "Truncate table {{logs}}", "code": "truncate_table(table='{{logs}}')"},
                    {"text": "Clear all rows from table {{sessions}}", "code": "truncate_table(table='{{sessions}}')"},
                ]
            ),
            MethodInfo(
                name="get_cluster_info",
                description="Get information about the Cassandra cluster",
                parameters={},
                returns="Dict with cluster_name, all_hosts, keyspaces, protocol_version",
                examples=[
                    {"text": "Get cluster information", "code": "get_cluster_info()"},
                    {"text": "Retrieve cluster status and metadata", "code": "get_cluster_info()"},
                ]
            ),
        ]

