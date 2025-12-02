"""
Redis Module for Caching and Key-Value Store

This module provides connection management for Redis.
Configuration is loaded from nl2py.conf under the [redis] section.

Supports:
- No authentication (default)
- Password authentication (AUTH)
- ACL username/password authentication (Redis 6+)
- SSL/TLS connections
- SSL/TLS without certificate verification (for development)
- Connection pooling
- All Redis data types: strings, hashes, lists, sets, sorted sets
- Pub/Sub messaging
- Transactions
- Pipelining

Example configuration in nl2py.conf:
    [redis]
    HOST=localhost
    PORT=6379
    DB=0
    PASSWORD=secret

    # SSL/TLS Settings (optional)
    USE_SSL=false
    SSL_VERIFY=true
    SSL_CA_CERT=/path/to/ca.pem
    SSL_CLIENT_CERT=/path/to/client-cert.pem
    SSL_CLIENT_KEY=/path/to/client-key.pem

    # ACL (Redis 6+)
    USERNAME=default

    # Connection Pool
    MAX_CONNECTIONS=50
    SOCKET_TIMEOUT=5
    SOCKET_CONNECT_TIMEOUT=5

Usage in generated code:
    from nl2py.modules import RedisModule

    # Initialize module (happens once per program)
    redis = RedisModule.from_config(config_path="nl2py.conf")

    # Basic operations
    redis.set('key', 'value', ex=3600)
    value = redis.get('key')

    # Hash operations
    redis.hset('user:123', mapping={'name': 'Alice', 'age': 30})
    user = redis.hgetall('user:123')

    # List operations
    redis.lpush('queue', 'task1', 'task2')
    task = redis.rpop('queue')
"""

import configparser
import json
import ssl
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

import redis
from redis import Redis, ConnectionPool
from .module_base import NL2PyModuleBase


class RedisModule(NL2PyModuleBase):
    """
    Redis connection manager with pooling and full SSL/TLS support.

    Supports all Redis operations and authentication methods.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        username: Optional[str] = None,
        use_ssl: bool = False,
        ssl_verify: bool = True,
        ssl_ca_cert: Optional[str] = None,
        ssl_client_cert: Optional[str] = None,
        ssl_client_key: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = True
    ):
        """
        Initialize the Redis module.

        Args:
            host: Redis host
            port: Redis port (default 6379, 6380 for SSL)
            db: Database number (0-15)
            password: Password for AUTH command
            username: Username for ACL (Redis 6+)
            use_ssl: Enable SSL/TLS connection
            ssl_verify: Verify SSL certificates (set False for self-signed)
            ssl_ca_cert: Path to CA certificate file
            ssl_client_cert: Path to client certificate file
            ssl_client_key: Path to client key file
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            decode_responses: Decode responses to strings (vs bytes)
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.username = username
        self.use_ssl = use_ssl
        self.ssl_verify = ssl_verify
        self.max_connections = max_connections
        self.decode_responses = decode_responses

        # Build connection parameters
        connection_params = {
            'host': host,
            'port': port,
            'db': db,
            'password': password,
            'username': username,
            'max_connections': max_connections,
            'socket_timeout': socket_timeout,
            'socket_connect_timeout': socket_connect_timeout,
            'decode_responses': decode_responses,
        }

        # SSL/TLS configuration
        if use_ssl:
            connection_params['ssl'] = True

            # SSL certificate verification
            if not ssl_verify:
                # Skip certificate verification
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connection_params['ssl_cert_reqs'] = ssl.CERT_NONE
                print("[RedisModule] ⚠️  SSL certificate verification DISABLED")
            else:
                # Verify certificates
                if ssl_ca_cert:
                    connection_params['ssl_ca_certs'] = ssl_ca_cert

                connection_params['ssl_cert_reqs'] = ssl.CERT_REQUIRED

            # Client certificates
            if ssl_client_cert:
                connection_params['ssl_certfile'] = ssl_client_cert
            if ssl_client_key:
                connection_params['ssl_keyfile'] = ssl_client_key

        # Create connection pool
        self.pool = ConnectionPool(**connection_params)
        self.client = Redis(connection_pool=self.pool)

        # Test connection
        try:
            self.client.ping()
            auth_info = f"{username}@" if username else ""
            print(f"[RedisModule] Connected to Redis: {auth_info}{host}:{port}/{db}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf") -> 'RedisModule':
        """
        Create a RedisModule from configuration file.
        Uses singleton pattern to ensure only one pool exists.

        Args:
            config_path: Path to nl2py.conf file

        Returns:
            RedisModule instance

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

                if 'redis' not in config:
                    raise KeyError("Missing [redis] section in nl2py.conf")

                redis_config = config['redis']

                # Connection
                host = redis_config.get('HOST', 'localhost')
                port = redis_config.getint('PORT', 6379)
                db = redis_config.getint('DB', 0)
                password = redis_config.get('PASSWORD', None)
                username = redis_config.get('USERNAME', None)

                # SSL/TLS
                use_ssl = redis_config.getboolean('USE_SSL', False)
                ssl_verify = redis_config.getboolean('SSL_VERIFY', True)
                ssl_ca_cert = redis_config.get('SSL_CA_CERT', None)
                ssl_client_cert = redis_config.get('SSL_CLIENT_CERT', None)
                ssl_client_key = redis_config.get('SSL_CLIENT_KEY', None)

                # Pool settings
                max_connections = redis_config.getint('MAX_CONNECTIONS', 50)
                socket_timeout = redis_config.getint('SOCKET_TIMEOUT', 5)
                socket_connect_timeout = redis_config.getint('SOCKET_CONNECT_TIMEOUT', 5)
                decode_responses = redis_config.getboolean('DECODE_RESPONSES', True)

                cls._instance = cls(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    username=username,
                    use_ssl=use_ssl,
                    ssl_verify=ssl_verify,
                    ssl_ca_cert=ssl_ca_cert,
                    ssl_client_cert=ssl_client_cert,
                    ssl_client_key=ssl_client_key,
                    max_connections=max_connections,
                    socket_timeout=socket_timeout,
                    socket_connect_timeout=socket_connect_timeout,
                    decode_responses=decode_responses
                )

            return cls._instance

    # ==================== String Operations ====================

    def set(self, key: str, value: Any, ex: Optional[int] = None, px: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """Set key to value with optional expiration."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)

    def get(self, key: str) -> Optional[str]:
        """Get value of key."""
        value = self.client.get(key)
        if value and self.decode_responses:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def mset(self, mapping: Dict[str, Any]) -> bool:
        """Set multiple keys to multiple values."""
        processed = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in mapping.items()}
        return self.client.mset(processed)

    def mget(self, keys: List[str]) -> List[Optional[str]]:
        """Get values of multiple keys."""
        return self.client.mget(keys)

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment key by amount."""
        return self.client.incr(key, amount)

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement key by amount."""
        return self.client.decr(key, amount)

    # ==================== Hash Operations ====================

    def hset(self, key: str, field: str = None, value: Any = None, mapping: Dict = None) -> int:
        """Set hash field to value or set multiple fields."""
        if mapping:
            return self.client.hset(key, mapping=mapping)
        return self.client.hset(key, field, value)

    def hget(self, key: str, field: str) -> Optional[str]:
        """Get value of hash field."""
        return self.client.hget(key, field)

    def hgetall(self, key: str) -> Dict:
        """Get all fields and values in hash."""
        return self.client.hgetall(key)

    def hdel(self, key: str, *fields: str) -> int:
        """Delete one or more hash fields."""
        return self.client.hdel(key, *fields)

    def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment hash field by amount."""
        return self.client.hincrby(key, field, amount)

    # ==================== List Operations ====================

    def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of list."""
        return self.client.lpush(key, *values)

    def rpush(self, key: str, *values: Any) -> int:
        """Push values to the right of list."""
        return self.client.rpush(key, *values)

    def lpop(self, key: str) -> Optional[str]:
        """Pop value from left of list."""
        return self.client.lpop(key)

    def rpop(self, key: str) -> Optional[str]:
        """Pop value from right of list."""
        return self.client.rpop(key)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range of elements from list."""
        return self.client.lrange(key, start, end)

    def llen(self, key: str) -> int:
        """Get length of list."""
        return self.client.llen(key)

    # ==================== Set Operations ====================

    def sadd(self, key: str, *members: Any) -> int:
        """Add members to set."""
        return self.client.sadd(key, *members)

    def srem(self, key: str, *members: Any) -> int:
        """Remove members from set."""
        return self.client.srem(key, *members)

    def smembers(self, key: str) -> set:
        """Get all members of set."""
        return self.client.smembers(key)

    def sismember(self, key: str, member: Any) -> bool:
        """Check if member is in set."""
        return self.client.sismember(key, member)

    # ==================== Sorted Set Operations ====================

    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Add members with scores to sorted set."""
        return self.client.zadd(key, mapping)

    def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> List:
        """Get range of members from sorted set."""
        return self.client.zrange(key, start, end, withscores=withscores)

    def zrem(self, key: str, *members: Any) -> int:
        """Remove members from sorted set."""
        return self.client.zrem(key, *members)

    def zscore(self, key: str, member: Any) -> Optional[float]:
        """Get score of member in sorted set."""
        return self.client.zscore(key, member)

    # ==================== Key Operations ====================

    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        return self.client.delete(*keys)

    def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        return self.client.exists(*keys)

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key in seconds."""
        return self.client.expire(key, seconds)

    def ttl(self, key: str) -> int:
        """Get time to live of key in seconds."""
        return self.client.ttl(key)

    def keys(self, pattern: str = '*') -> List[str]:
        """Get all keys matching pattern."""
        return self.client.keys(pattern)

    def scan(self, cursor: int = 0, match: str = None, count: int = 10):
        """Scan keys incrementally."""
        return self.client.scan(cursor, match, count)

    # ==================== Pub/Sub Operations ====================

    def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel."""
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        return self.client.publish(channel, message)

    def subscribe(self, *channels: str):
        """Subscribe to channels (returns pubsub object)."""
        pubsub = self.client.pubsub()
        pubsub.subscribe(*channels)
        return pubsub

    # ==================== Transaction/Pipeline Operations ====================

    def pipeline(self, transaction: bool = True):
        """Create a pipeline for batch operations."""
        return self.client.pipeline(transaction=transaction)

    # ==================== Utility Operations ====================

    def flushdb(self):
        """Delete all keys in current database."""
        return self.client.flushdb()

    def flushall(self):
        """Delete all keys in all databases."""
        return self.client.flushall()

    def ping(self) -> bool:
        """Ping Redis server."""
        return self.client.ping()

    def info(self, section: str = None) -> Dict:
        """Get Redis server information."""
        return self.client.info(section)

    def dbsize(self) -> int:
        """Get number of keys in current database."""
        return self.client.dbsize()

    def close(self):
        """Close connection pool."""
        if self.pool:
            self.pool.disconnect()
            print("[RedisModule] Connection pool closed")

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get current connection information.

        Returns:
            dict: Connection details
        """
        return {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "username": self.username,
            "use_ssl": self.use_ssl,
            "ssl_verify": self.ssl_verify,
            "max_connections": self.max_connections
        }

    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="Redis",
            task_type="redis",
            description="Redis key-value store and caching with support for all data types, Pub/Sub, transactions, and SSL/TLS",
            version="1.0.0",
            keywords=[
                "redis", "cache", "key-value", "nosql", "pubsub", "messaging",
                "hash", "list", "set", "sorted-set", "transaction", "pipeline", "ssl"
            ],
            dependencies=["redis>=4.0.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern - one connection pool per application",
            "Connection pool configured via MAX_CONNECTIONS (default 50)",
            "Supports password authentication (AUTH) and ACL username/password (Redis 6+)",
            "SSL/TLS connections supported with optional certificate verification",
            "Set SSL_VERIFY=false for self-signed certificates (development only)",
            "Default database is 0, configurable via DB parameter (0-15)",
            "decode_responses=True returns strings instead of bytes",
            "JSON values automatically serialized/deserialized in set/get",
            "Expiration can be set in seconds (ex) or milliseconds (px)",
            "nx=True sets only if key doesn't exist, xx=True sets only if exists",
            "Hash operations support both single field and mapping (multiple fields)",
            "List operations: lpush/lpop for left side, rpush/rpop for right side",
            "Sorted sets store members with scores for ranking/leaderboards",
            "Pub/Sub returns pubsub object - call get_message() to receive",
            "Pipeline groups multiple commands for batch execution",
            "scan() preferred over keys() for production (non-blocking iteration)",
            "ttl() returns -1 for keys without expiration, -2 for non-existent keys",
            "Socket timeout defaults to 5 seconds, configurable via SOCKET_TIMEOUT",
            "Connection tested with ping() on initialization",
            "Call close() to cleanup connection pool when done"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="set",
                description="Set key to value with optional expiration and conditions",
                parameters={
                    "key": "str (required) - Key name",
                    "value": "Any (required) - Value to store (auto-serializes dict/list to JSON)",
                    "ex": "int (optional) - Expiration in seconds",
                    "px": "int (optional) - Expiration in milliseconds",
                    "nx": "bool (optional) - Set only if key doesn't exist",
                    "xx": "bool (optional) - Set only if key exists"
                },
                returns="bool - True if successful",
                examples=[
                    {"text": "Set key {{user:123}} to value {{John Doe}}", "code": "set(key='{{user:123}}', value='{{John Doe}}')"},
                    {"text": "Set key {{session:abc}} to JSON value with expiration {{3600}} seconds", "code": "set(key='{{session:abc}}', value={{{'user_id': 123}}}, ex={{3600}})"}
                ]
            ),
            MethodInfo(
                name="get",
                description="Get value of key (auto-deserializes JSON)",
                parameters={"key": "str (required) - Key name"},
                returns="str/dict/list/None - Value or None if key doesn't exist",
                examples=[
                    {"text": "Get value from key {{user:123}}", "code": "get(key='{{user:123}}')"},
                    {"text": "Get value from key {{session:abc}}", "code": "get(key='{{session:abc}}')"}
                ]
            ),
            MethodInfo(
                name="hset",
                description="Set hash field to value or set multiple fields",
                parameters={
                    "key": "str (required) - Hash key name",
                    "field": "str (optional) - Field name",
                    "value": "Any (optional) - Field value",
                    "mapping": "dict (optional) - Multiple field-value pairs"
                },
                returns="int - Number of fields added",
                examples=[
                    {"text": "Set hash field {{name}} to {{Alice}} in key {{user:123}}", "code": "hset(key='{{user:123}}', field='{{name}}', value='{{Alice}}')"},
                    {"text": "Set multiple hash fields in key {{user:123}}", "code": "hset(key='{{user:123}}', mapping={{'name': 'Alice', 'age': 30}})"}
                ]
            ),
            MethodInfo(
                name="hgetall",
                description="Get all fields and values in hash",
                parameters={"key": "str (required) - Hash key name"},
                returns="dict - All field-value pairs",
                examples=[
                    {"text": "Get all fields from hash {{user:123}}", "code": "hgetall(key='{{user:123}}')"}
                ]
            ),
            MethodInfo(
                name="lpush",
                description="Push values to the left (head) of list",
                parameters={
                    "key": "str (required) - List key name",
                    "values": "Any (variadic) - Values to push"
                },
                returns="int - New length of list",
                examples=[
                    {"text": "Push values {{task1}} and {{task2}} to list {{queue}}", "code": "lpush(key='{{queue}}', values='{{task1}}', '{{task2}}')"},
                    {"text": "Push value {{process_order}} to list {{jobs}}", "code": "lpush(key='{{jobs}}', values='{{process_order}}')"}
                ]
            ),
            MethodInfo(
                name="rpop",
                description="Pop and return value from the right (tail) of list",
                parameters={"key": "str (required) - List key name"},
                returns="str/None - Popped value or None if list is empty",
                examples=[
                    {"text": "Pop value from right of list {{queue}}", "code": "rpop(key='{{queue}}')"},
                    {"text": "Pop value from right of list {{jobs}}", "code": "rpop(key='{{jobs}}')"}
                ]
            ),
            MethodInfo(
                name="sadd",
                description="Add members to set",
                parameters={
                    "key": "str (required) - Set key name",
                    "members": "Any (variadic) - Members to add"
                },
                returns="int - Number of members added",
                examples=[
                    {"text": "Add members {{python}}, {{redis}}, and {{cache}} to set {{tags}}", "code": "sadd(key='{{tags}}', members='{{python}}', '{{redis}}', '{{cache}}')"}
                ]
            ),
            MethodInfo(
                name="smembers",
                description="Get all members of set",
                parameters={"key": "str (required) - Set key name"},
                returns="set - All members",
                examples=[
                    {"text": "Get all members from set {{tags}}", "code": "smembers(key='{{tags}}')"}
                ]
            ),
            MethodInfo(
                name="zadd",
                description="Add members with scores to sorted set",
                parameters={
                    "key": "str (required) - Sorted set key name",
                    "mapping": "dict (required) - Member-score pairs {member: score}"
                },
                returns="int - Number of members added",
                examples=[
                    {"text": "Add members with scores to sorted set {{leaderboard}}", "code": "zadd(key='{{leaderboard}}', mapping={{'player1': 100, 'player2': 200}})"}
                ]
            ),
            MethodInfo(
                name="zrange",
                description="Get range of members from sorted set by rank",
                parameters={
                    "key": "str (required) - Sorted set key name",
                    "start": "int (required) - Start index (0-based)",
                    "end": "int (required) - End index (-1 for all)",
                    "withscores": "bool (optional) - Include scores in result"
                },
                returns="list - Members or (member, score) tuples if withscores=True",
                examples=[
                    {"text": "Get top 10 members from sorted set {{leaderboard}}", "code": "zrange(key='{{leaderboard}}', start={{0}}, end={{9}})"},
                    {"text": "Get all members with scores from sorted set {{leaderboard}}", "code": "zrange(key='{{leaderboard}}', start={{0}}, end={{-1}}, withscores=True)"}
                ]
            ),
            MethodInfo(
                name="publish",
                description="Publish message to Pub/Sub channel",
                parameters={
                    "channel": "str (required) - Channel name",
                    "message": "Any (required) - Message to publish (auto-serializes dict/list)"
                },
                returns="int - Number of subscribers that received the message",
                examples=[
                    {"text": "Publish message {{New order received}} to channel {{notifications}}", "code": "publish(channel='{{notifications}}', message='{{New order received}}')"},
                    {"text": "Publish JSON message to channel {{events}}", "code": "publish(channel='{{events}}', message={{'type': 'login', 'user': 123}})"}
                ]
            ),
            MethodInfo(
                name="subscribe",
                description="Subscribe to Pub/Sub channels",
                parameters={"channels": "str (variadic) - Channel names to subscribe to"},
                returns="PubSub - PubSub object (call get_message() to receive)",
                examples=[
                    {"text": "Subscribe to channels {{notifications}} and {{alerts}}", "code": "subscribe(channels='{{notifications}}', '{{alerts}}')"}
                ]
            ),
            MethodInfo(
                name="expire",
                description="Set expiration on key in seconds",
                parameters={
                    "key": "str (required) - Key name",
                    "seconds": "int (required) - Expiration time in seconds"
                },
                returns="bool - True if successful",
                examples=[
                    {"text": "Set expiration of key {{session:abc}} to {{3600}} seconds", "code": "expire(key='{{session:abc}}', seconds={{3600}})"},
                    {"text": "Set expiration of key {{temp_data}} to {{300}} seconds", "code": "expire(key='{{temp_data}}', seconds={{300}})"}
                ]
            ),
            MethodInfo(
                name="ttl",
                description="Get time to live of key in seconds",
                parameters={"key": "str (required) - Key name"},
                returns="int - Seconds until expiration, -1 if no expiration, -2 if key doesn't exist",
                examples=[
                    {"text": "Get time to live for key {{session:abc}}", "code": "ttl(key='{{session:abc}}')"}
                ]
            ),
            MethodInfo(
                name="delete",
                description="Delete one or more keys",
                parameters={"keys": "str (variadic) - Key names to delete"},
                returns="int - Number of keys deleted",
                examples=[
                    {"text": "Delete key {{temp:123}}", "code": "delete(keys='{{temp:123}}')"},
                    {"text": "Delete keys {{cache:1}}, {{cache:2}}, and {{cache:3}}", "code": "delete(keys='{{cache:1}}', '{{cache:2}}', '{{cache:3}}')"}
                ]
            ),
            MethodInfo(
                name="pipeline",
                description="Create pipeline for batch operations",
                parameters={"transaction": "bool (optional) - Use transaction (default True)"},
                returns="Pipeline - Pipeline object for batching commands",
                examples=[
                    {"text": "Create pipeline", "code": "pipeline()"},
                    {"text": "Create non-transactional pipeline", "code": "pipeline(transaction=False)"}
                ]
            ),
            # Additional String Operations
            MethodInfo(
                name="mset",
                description="Set multiple keys to multiple values atomically",
                parameters={"mapping": "dict (required) - Key-value pairs to set"},
                returns="bool - True if successful",
                examples=[
                    {"text": "Set multiple keys at once", "code": "mset(mapping={{'user:1': 'Alice', 'user:2': 'Bob'}})"}
                ]
            ),
            MethodInfo(
                name="mget",
                description="Get values of multiple keys at once",
                parameters={"keys": "list (required) - List of key names"},
                returns="list - Values in same order as keys (None for missing keys)",
                examples=[
                    {"text": "Get values from keys {{user:1}}, {{user:2}}, and {{user:3}}", "code": "mget(keys=['{{user:1}}', '{{user:2}}', '{{user:3}}'])"}
                ]
            ),
            MethodInfo(
                name="incr",
                description="Increment numeric value of key",
                parameters={
                    "key": "str (required) - Key name",
                    "amount": "int (optional) - Amount to increment (default 1)"
                },
                returns="int - New value after increment",
                examples=[
                    {"text": "Increment counter {{counter}} by 1", "code": "incr(key='{{counter}}')"},
                    {"text": "Increment key {{page_views}} by {{5}}", "code": "incr(key='{{page_views}}', amount={{5}})"}
                ]
            ),
            MethodInfo(
                name="decr",
                description="Decrement numeric value of key",
                parameters={
                    "key": "str (required) - Key name",
                    "amount": "int (optional) - Amount to decrement (default 1)"
                },
                returns="int - New value after decrement",
                examples=[
                    {"text": "Decrement counter {{inventory:item1}} by 1", "code": "decr(key='{{inventory:item1}}')"},
                    {"text": "Decrement key {{stock}} by {{10}}", "code": "decr(key='{{stock}}', amount={{10}})"}
                ]
            ),
            # Additional Hash Operations
            MethodInfo(
                name="hget",
                description="Get value of specific hash field",
                parameters={
                    "key": "str (required) - Hash key name",
                    "field": "str (required) - Field name"
                },
                returns="str/None - Field value or None if not exists",
                examples=[
                    {"text": "Get field {{email}} from hash {{user:123}}", "code": "hget(key='{{user:123}}', field='{{email}}')"}
                ]
            ),
            MethodInfo(
                name="hdel",
                description="Delete one or more hash fields",
                parameters={
                    "key": "str (required) - Hash key name",
                    "fields": "str (variadic) - Field names to delete"
                },
                returns="int - Number of fields deleted",
                examples=[
                    {"text": "Delete field {{temp_field}} from hash {{user:123}}", "code": "hdel(key='{{user:123}}', fields='{{temp_field}}')"},
                    {"text": "Delete fields {{token}} and {{refresh_token}} from hash {{session:abc}}", "code": "hdel(key='{{session:abc}}', fields='{{token}}', '{{refresh_token}}')"}
                ]
            ),
            MethodInfo(
                name="hincrby",
                description="Increment hash field by integer amount",
                parameters={
                    "key": "str (required) - Hash key name",
                    "field": "str (required) - Field name",
                    "amount": "int (optional) - Amount to increment (default 1)"
                },
                returns="int - New value after increment",
                examples=[
                    {"text": "Increment field {{login_count}} in hash {{user:123}} by {{1}}", "code": "hincrby(key='{{user:123}}', field='{{login_count}}', amount={{1}})"}
                ]
            ),
            # Additional List Operations
            MethodInfo(
                name="rpush",
                description="Push values to the right (tail) of list",
                parameters={
                    "key": "str (required) - List key name",
                    "values": "Any (variadic) - Values to push"
                },
                returns="int - New length of list",
                examples=[
                    {"text": "Push values {{entry1}} and {{entry2}} to right of list {{logs}}", "code": "rpush(key='{{logs}}', values='{{entry1}}', '{{entry2}}')"}
                ]
            ),
            MethodInfo(
                name="lpop",
                description="Pop and return value from the left (head) of list",
                parameters={"key": "str (required) - List key name"},
                returns="str/None - Popped value or None if list is empty",
                examples=[
                    {"text": "Pop value from left of list {{queue}}", "code": "lpop(key='{{queue}}')"}
                ]
            ),
            MethodInfo(
                name="lrange",
                description="Get range of elements from list",
                parameters={
                    "key": "str (required) - List key name",
                    "start": "int (required) - Start index (0-based)",
                    "end": "int (required) - End index (-1 for all)"
                },
                returns="list - Elements in range",
                examples=[
                    {"text": "Get first 10 elements from list {{mylist}}", "code": "lrange(key='{{mylist}}', start={{0}}, end={{9}})"},
                    {"text": "Get all elements from list {{logs}}", "code": "lrange(key='{{logs}}', start={{0}}, end={{-1}})"}
                ]
            ),
            MethodInfo(
                name="llen",
                description="Get length of list",
                parameters={"key": "str (required) - List key name"},
                returns="int - Number of elements in list",
                examples=[
                    {"text": "Get length of list {{queue}}", "code": "llen(key='{{queue}}')"}
                ]
            ),
            # Additional Set Operations
            MethodInfo(
                name="srem",
                description="Remove members from set",
                parameters={
                    "key": "str (required) - Set key name",
                    "members": "Any (variadic) - Members to remove"
                },
                returns="int - Number of members removed",
                examples=[
                    {"text": "Remove member {{old_tag}} from set {{tags}}", "code": "srem(key='{{tags}}', members='{{old_tag}}')"}
                ]
            ),
            MethodInfo(
                name="sismember",
                description="Check if member exists in set",
                parameters={
                    "key": "str (required) - Set key name",
                    "member": "Any (required) - Member to check"
                },
                returns="bool - True if member is in set",
                examples=[
                    {"text": "Check if member {{user123}} is in set {{users:active}}", "code": "sismember(key='{{users:active}}', member='{{user123}}')"}
                ]
            ),
            # Additional Sorted Set Operations
            MethodInfo(
                name="zrem",
                description="Remove members from sorted set",
                parameters={
                    "key": "str (required) - Sorted set key name",
                    "members": "Any (variadic) - Members to remove"
                },
                returns="int - Number of members removed",
                examples=[
                    {"text": "Remove member {{player1}} from sorted set {{leaderboard}}", "code": "zrem(key='{{leaderboard}}', members='{{player1}}')"}
                ]
            ),
            MethodInfo(
                name="zscore",
                description="Get score of member in sorted set",
                parameters={
                    "key": "str (required) - Sorted set key name",
                    "member": "Any (required) - Member name"
                },
                returns="float/None - Score or None if member not found",
                examples=[
                    {"text": "Get score of member {{player1}} in sorted set {{leaderboard}}", "code": "zscore(key='{{leaderboard}}', member='{{player1}}')"}
                ]
            ),
            # Additional Key Operations
            MethodInfo(
                name="exists",
                description="Check if keys exist",
                parameters={"keys": "str (variadic) - Key names to check"},
                returns="int - Number of keys that exist",
                examples=[
                    {"text": "Check if key {{user:123}} exists", "code": "exists(keys='{{user:123}}')"},
                    {"text": "Check if keys {{key1}}, {{key2}}, and {{key3}} exist", "code": "exists(keys='{{key1}}', '{{key2}}', '{{key3}}')"}
                ]
            ),
            MethodInfo(
                name="keys",
                description="Find all keys matching pattern (use sparingly in production)",
                parameters={"pattern": "str (optional) - Glob-style pattern (default '*')"},
                returns="list - Matching key names",
                examples=[
                    {"text": "Find all keys matching pattern {{user:*}}", "code": "keys(pattern='{{user:*}}')"},
                    {"text": "Find all keys matching pattern {{session:*}}", "code": "keys(pattern='{{session:*}}')"}
                ]
            ),
            MethodInfo(
                name="scan",
                description="Incrementally iterate keys (preferred over keys for large datasets)",
                parameters={
                    "cursor": "int (optional) - Cursor position (default 0)",
                    "match": "str (optional) - Pattern to match",
                    "count": "int (optional) - Hint for number of keys (default 10)"
                },
                returns="tuple - (new_cursor, list of keys)",
                examples=[
                    {"text": "Scan keys matching pattern {{user:*}} with count {{100}}", "code": "scan(cursor={{0}}, match='{{user:*}}', count={{100}})"}
                ]
            ),
            # Utility Operations
            MethodInfo(
                name="ping",
                description="Ping Redis server to check connection",
                parameters={},
                returns="bool - True if server responds",
                examples=[
                    {"text": "Ping Redis server", "code": "ping()"}
                ]
            ),
            MethodInfo(
                name="info",
                description="Get Redis server information and statistics",
                parameters={"section": "str (optional) - Specific section (server, clients, memory, stats, etc.)"},
                returns="dict - Server information",
                examples=[
                    {"text": "Get all server information", "code": "info()"},
                    {"text": "Get server info for section {{memory}}", "code": "info(section='{{memory}}')"}
                ]
            ),
            MethodInfo(
                name="dbsize",
                description="Get number of keys in current database",
                parameters={},
                returns="int - Number of keys",
                examples=[
                    {"text": "Get database size", "code": "dbsize()"}
                ]
            ),
            MethodInfo(
                name="flushdb",
                description="Delete all keys in current database (dangerous!)",
                parameters={},
                returns="bool - True if successful",
                examples=[
                    {"text": "Flush current database", "code": "flushdb()"}
                ]
            ),
            MethodInfo(
                name="flushall",
                description="Delete all keys in all databases (very dangerous!)",
                parameters={},
                returns="bool - True if successful",
                examples=[
                    {"text": "Flush all databases", "code": "flushall()"}
                ]
            )
        ]

