"""
RabbitMQ Module for Message Publishing and Consumption

This module provides connection management for RabbitMQ message broker.
Configuration is loaded from nl2py.conf under the [rabbitmq] section.

Supports:
- Basic authentication (username/password)
- External authentication (EXTERNAL mechanism)
- SSL/TLS with certificate verification
- SSL/TLS without certificate verification (for development)
- Connection pooling and automatic reconnection

Example configuration in nl2py.conf:
    [rabbitmq]
    HOST=localhost
    PORT=5672
    VHOST=/
    USERNAME=guest
    PASSWORD=guest

    # SSL/TLS settings (optional)
    USE_SSL=false
    SSL_VERIFY=true
    SSL_CA_CERT=/path/to/ca_cert.pem
    SSL_CLIENT_CERT=/path/to/client_cert.pem
    SSL_CLIENT_KEY=/path/to/client_key.pem

    # Connection settings
    HEARTBEAT=60
    BLOCKED_CONNECTION_TIMEOUT=300
    CONNECTION_ATTEMPTS=3
    RETRY_DELAY=2

Usage in generated code:
    from nl2py.modules import RabbitMQModule

    # Initialize module (happens once per program)
    rmq = RabbitMQModule.from_config(config_path="nl2py.conf")

    # Publish a message
    rmq.publish_message(
        exchange='my_exchange',
        routing_key='my.routing.key',
        message={'data': 'value'},
        properties={'content_type': 'application/json'}
    )

    # Consume messages
    def callback(ch, method, properties, body):
        print(f"Received: {body}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    rmq.consume_messages(queue='my_queue', callback=callback)
"""

import configparser
import json
import ssl
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Union

import pika
from pika import BasicProperties
from .module_base import NL2PyModuleBase


class RabbitMQModule(NL2PyModuleBase):
    """
    RabbitMQ connection manager with support for publishing and consuming messages.

    Supports multiple authentication methods and flexible SSL/TLS configuration.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(
        self,
        host: str,
        port: int = 5672,
        vhost: str = '/',
        username: str = 'guest',
        password: str = 'guest',
        use_ssl: bool = False,
        ssl_verify: bool = True,
        ssl_ca_cert: Optional[str] = None,
        ssl_client_cert: Optional[str] = None,
        ssl_client_key: Optional[str] = None,
        heartbeat: int = 60,
        blocked_connection_timeout: int = 300,
        connection_attempts: int = 3,
        retry_delay: int = 2
    ):
        """
        Initialize the RabbitMQ connection manager.

        Args:
            host: RabbitMQ host address
            port: RabbitMQ port (5672 for AMQP, 5671 for AMQPS)
            vhost: Virtual host
            username: Username for authentication
            password: Password for authentication
            use_ssl: Enable SSL/TLS connection
            ssl_verify: Verify SSL certificates (set False for self-signed)
            ssl_ca_cert: Path to CA certificate file
            ssl_client_cert: Path to client certificate file
            ssl_client_key: Path to client key file
            heartbeat: Heartbeat interval in seconds
            blocked_connection_timeout: Timeout for blocked connections
            connection_attempts: Number of connection attempts
            retry_delay: Delay between connection attempts
        """
        self.host = host
        self.port = port
        self.vhost = vhost
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.ssl_verify = ssl_verify
        self.ssl_ca_cert = ssl_ca_cert
        self.ssl_client_cert = ssl_client_cert
        self.ssl_client_key = ssl_client_key
        self.heartbeat = heartbeat
        self.blocked_connection_timeout = blocked_connection_timeout
        self.connection_attempts = connection_attempts
        self.retry_delay = retry_delay

        self._connection = None
        self._channel = None
        self._connect()

        print(f"[RabbitMQModule] Connected to RabbitMQ: {username}@{host}:{port}{vhost}")

    def _connect(self):
        """Establish connection to RabbitMQ with configured settings."""
        # Create credentials
        credentials = pika.PlainCredentials(self.username, self.password)

        # Configure SSL/TLS if enabled
        ssl_options = None
        if self.use_ssl:
            ssl_context = ssl.create_default_context()

            # Handle certificate verification
            if not self.ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                print("[RabbitMQModule] SSL certificate verification DISABLED")
            else:
                ssl_context.verify_mode = ssl.CERT_REQUIRED

                # Load CA certificate if provided
                if self.ssl_ca_cert:
                    ssl_context.load_verify_locations(cafile=self.ssl_ca_cert)

            # Load client certificate and key if provided
            if self.ssl_client_cert and self.ssl_client_key:
                ssl_context.load_cert_chain(
                    certfile=self.ssl_client_cert,
                    keyfile=self.ssl_client_key
                )

            ssl_options = pika.SSLOptions(ssl_context)

        # Create connection parameters
        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=credentials,
            ssl_options=ssl_options,
            heartbeat=self.heartbeat,
            blocked_connection_timeout=self.blocked_connection_timeout,
            connection_attempts=self.connection_attempts,
            retry_delay=self.retry_delay
        )

        try:
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to RabbitMQ: {e}")

    @classmethod
    def from_config(cls, config_path: str = "nl2py.conf") -> 'RabbitMQModule':
        """
        Create a RabbitMQModule from configuration file.
        Uses singleton pattern to ensure only one connection exists.

        Args:
            config_path: Path to nl2py.conf file

        Returns:
            RabbitMQModule instance

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

                if 'rabbitmq' not in config:
                    raise KeyError("Missing [rabbitmq] section in nl2py.conf")

                rmq_config = config['rabbitmq']

                # Required fields
                host = rmq_config.get('HOST')
                port = rmq_config.getint('PORT', 5672)
                vhost = rmq_config.get('VHOST', '/')
                username = rmq_config.get('USERNAME', 'guest')
                password = rmq_config.get('PASSWORD', 'guest')

                # SSL/TLS settings
                use_ssl = rmq_config.getboolean('USE_SSL', False)
                ssl_verify = rmq_config.getboolean('SSL_VERIFY', True)
                ssl_ca_cert = rmq_config.get('SSL_CA_CERT', None)
                ssl_client_cert = rmq_config.get('SSL_CLIENT_CERT', None)
                ssl_client_key = rmq_config.get('SSL_CLIENT_KEY', None)

                # Connection settings
                heartbeat = rmq_config.getint('HEARTBEAT', 60)
                blocked_timeout = rmq_config.getint('BLOCKED_CONNECTION_TIMEOUT', 300)
                conn_attempts = rmq_config.getint('CONNECTION_ATTEMPTS', 3)
                retry_delay = rmq_config.getint('RETRY_DELAY', 2)

                if not host:
                    raise KeyError("Missing required rabbitmq configuration: HOST")

                cls._instance = cls(
                    host=host,
                    port=port,
                    vhost=vhost,
                    username=username,
                    password=password,
                    use_ssl=use_ssl,
                    ssl_verify=ssl_verify,
                    ssl_ca_cert=ssl_ca_cert,
                    ssl_client_cert=ssl_client_cert,
                    ssl_client_key=ssl_client_key,
                    heartbeat=heartbeat,
                    blocked_connection_timeout=blocked_timeout,
                    connection_attempts=conn_attempts,
                    retry_delay=retry_delay
                )

            return cls._instance

    def _ensure_connection(self):
        """Ensure connection is alive, reconnect if necessary."""
        if self._connection is None or self._connection.is_closed:
            print("[RabbitMQModule] Reconnecting to RabbitMQ...")
            self._connect()

    def declare_exchange(
        self,
        exchange: str,
        exchange_type: str = 'direct',
        durable: bool = True,
        auto_delete: bool = False
    ):
        """
        Declare an exchange.

        Args:
            exchange: Exchange name
            exchange_type: Exchange type (direct, topic, fanout, headers)
            durable: Exchange survives broker restart
            auto_delete: Exchange is deleted when last queue is unbound
        """
        self._ensure_connection()
        self._channel.exchange_declare(
            exchange=exchange,
            exchange_type=exchange_type,
            durable=durable,
            auto_delete=auto_delete
        )
        print(f"[RabbitMQModule] Exchange declared: {exchange} ({exchange_type})")

    def declare_queue(
        self,
        queue: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict] = None
    ):
        """
        Declare a queue.

        Args:
            queue: Queue name
            durable: Queue survives broker restart
            exclusive: Queue is exclusive to this connection
            auto_delete: Queue is deleted when last consumer disconnects
            arguments: Optional queue arguments (e.g., TTL, max length)
        """
        self._ensure_connection()
        result = self._channel.queue_declare(
            queue=queue,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=arguments
        )
        print(f"[RabbitMQModule] Queue declared: {queue}")
        return result

    def bind_queue(self, queue: str, exchange: str, routing_key: str = ''):
        """
        Bind a queue to an exchange with a routing key.

        Args:
            queue: Queue name
            exchange: Exchange name
            routing_key: Routing key pattern
        """
        self._ensure_connection()
        self._channel.queue_bind(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key
        )
        print(f"[RabbitMQModule] Queue bound: {queue} -> {exchange} [{routing_key}]")

    def publish_message(
        self,
        exchange: str,
        routing_key: str,
        message: Union[str, dict, bytes],
        properties: Optional[Dict[str, Any]] = None,
        mandatory: bool = False
    ):
        """
        Publish a message to an exchange.

        Args:
            exchange: Exchange name (empty string for default exchange)
            routing_key: Routing key
            message: Message body (str, dict, or bytes)
            properties: Message properties (content_type, delivery_mode, etc.)
            mandatory: If True, message must be routable

        Example:
            rmq.publish_message(
                exchange='my_exchange',
                routing_key='my.key',
                message={'data': 'value'},
                properties={'content_type': 'application/json', 'delivery_mode': 2}
            )
        """
        self._ensure_connection()

        # Convert message to bytes
        if isinstance(message, dict):
            body = json.dumps(message).encode('utf-8')
            if properties is None:
                properties = {}
            properties['content_type'] = 'application/json'
        elif isinstance(message, str):
            body = message.encode('utf-8')
        else:
            body = message

        # Create properties
        props = BasicProperties(**properties) if properties else None

        # Publish
        self._channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=body,
            properties=props,
            mandatory=mandatory
        )
        print(f"[RabbitMQModule] Message published: {exchange} -> {routing_key}")

    def consume_messages(
        self,
        queue: str,
        callback: Callable,
        auto_ack: bool = False,
        prefetch_count: int = 1
    ):
        """
        Start consuming messages from a queue.

        Args:
            queue: Queue name
            callback: Function to call for each message
                      Signature: callback(ch, method, properties, body)
            auto_ack: Automatically acknowledge messages
            prefetch_count: Number of messages to prefetch

        Example:
            def my_callback(ch, method, properties, body):
                print(f"Received: {body}")
                ch.basic_ack(delivery_tag=method.delivery_tag)

            rmq.consume_messages('my_queue', my_callback)
        """
        self._ensure_connection()

        self._channel.basic_qos(prefetch_count=prefetch_count)
        self._channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
            auto_ack=auto_ack
        )

        print(f"[RabbitMQModule] Started consuming from queue: {queue}")
        print("[RabbitMQModule] Press Ctrl+C to stop consuming")

        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self._channel.stop_consuming()
            print("\n[RabbitMQModule] Stopped consuming")

    def get_message(self, queue: str, auto_ack: bool = False):
        """
        Get a single message from a queue (non-blocking).

        Args:
            queue: Queue name
            auto_ack: Automatically acknowledge message

        Returns:
            Tuple of (method, properties, body) or (None, None, None) if no message
        """
        self._ensure_connection()

        method, properties, body = self._channel.basic_get(
            queue=queue,
            auto_ack=auto_ack
        )

        if method:
            print(f"[RabbitMQModule] Message retrieved from queue: {queue}")
            return method, properties, body
        else:
            return None, None, None

    def purge_queue(self, queue: str):
        """
        Purge all messages from a queue.

        Args:
            queue: Queue name
        """
        self._ensure_connection()
        self._channel.queue_purge(queue=queue)
        print(f"[RabbitMQModule] Queue purged: {queue}")

    def delete_queue(self, queue: str, if_unused: bool = False, if_empty: bool = False):
        """
        Delete a queue.

        Args:
            queue: Queue name
            if_unused: Delete only if no consumers
            if_empty: Delete only if empty
        """
        self._ensure_connection()
        self._channel.queue_delete(
            queue=queue,
            if_unused=if_unused,
            if_empty=if_empty
        )
        print(f"[RabbitMQModule] Queue deleted: {queue}")

    def close(self):
        """Close the connection to RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            self._connection.close()
            print("[RabbitMQModule] Connection closed")

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get current connection information.

        Returns:
            dict: Connection details
        """
        return {
            "host": self.host,
            "port": self.port,
            "vhost": self.vhost,
            "username": self.username,
            "use_ssl": self.use_ssl,
            "ssl_verify": self.ssl_verify,
            "is_connected": self._connection and not self._connection.is_closed
        }

    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="RabbitMQ",
            task_type="rabbitmq",
            description="RabbitMQ message broker for publishing/consuming messages with exchanges, queues, and routing",
            version="1.0.0",
            keywords=[
                "rabbitmq", "amqp", "messaging", "queue", "publish-subscribe",
                "exchange", "routing", "message-broker", "async", "ssl"
            ],
            dependencies=["pika>=1.2.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern with automatic reconnection",
            "Default port is 5672 for AMQP, 5671 for AMQPS (SSL)",
            "Supports basic authentication with username/password",
            "SSL/TLS supported with optional certificate verification",
            "Set SSL_VERIFY=false for self-signed certificates (development only)",
            "Virtual host (VHOST) defaults to '/' (root vhost)",
            "Exchange types: direct, topic, fanout, headers",
            "Durable exchanges/queues survive broker restart",
            "Messages auto-serialized to JSON if dict provided",
            "delivery_mode=2 makes messages persistent (survives restart)",
            "auto_ack=False requires manual ch.basic_ack() in callback",
            "prefetch_count limits unacknowledged messages per consumer",
            "consume_messages() blocks until Ctrl+C pressed",
            "get_message() non-blocking, returns (None, None, None) if empty",
            "Routing key binds queue to exchange (exact match for 'direct')",
            "Topic exchanges support wildcards: * (one word), # (zero or more words)",
            "Fanout exchanges broadcast to all bound queues (ignores routing key)",
            "Connection auto-reconnects if closed (via _ensure_connection)",
            "Heartbeat defaults to 60 seconds to detect dead connections",
            "Always acknowledge or reject messages to prevent queue buildup"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="declare_exchange",
                description="Declare an exchange for message routing",
                parameters={
                    "exchange": "str (required) - Exchange name",
                    "exchange_type": "str (optional) - Type: direct, topic, fanout, headers (default direct)",
                    "durable": "bool (optional) - Survives broker restart (default True)",
                    "auto_delete": "bool (optional) - Delete when last queue unbound (default False)"
                },
                returns="None",
                examples=[
                    {"text": "Declare exchange {{my_exchange}} exchange_type {{topic}}", "code": "declare_exchange(exchange='{{my_exchange}}', exchange_type='topic')"},
                    {"text": "Declare exchange {{logs}} exchange_type {{fanout}} durable {{True}}", "code": "declare_exchange(exchange='{{logs}}', exchange_type='fanout', durable=True)"}
                ]
            ),
            MethodInfo(
                name="declare_queue",
                description="Declare a queue for storing messages",
                parameters={
                    "queue": "str (required) - Queue name",
                    "durable": "bool (optional) - Survives broker restart (default True)",
                    "exclusive": "bool (optional) - Exclusive to this connection (default False)",
                    "auto_delete": "bool (optional) - Delete when last consumer disconnects (default False)",
                    "arguments": "dict (optional) - Queue arguments (TTL, max length, etc.)"
                },
                returns="Method frame with queue info",
                examples=[
                    {"text": "Declare queue {{tasks}}", "code": "declare_queue(queue='{{tasks}}')"},
                    {"text": "Declare queue {{temp}} exclusive {{True}} auto_delete {{True}}", "code": "declare_queue(queue='{{temp}}', exclusive=True, auto_delete=True)"}
                ]
            ),
            MethodInfo(
                name="bind_queue",
                description="Bind queue to exchange with routing key",
                parameters={
                    "queue": "str (required) - Queue name",
                    "exchange": "str (required) - Exchange name",
                    "routing_key": "str (optional) - Routing key pattern (default empty)"
                },
                returns="None",
                examples=[
                    {"text": "Bind queue {{tasks}} exchange {{my_exchange}} routing_key {{task.#}}", "code": "bind_queue(queue='{{tasks}}', exchange='{{my_exchange}}', routing_key='task.#')"},
                    {"text": "Bind queue {{logs}} exchange {{fanout_logs}}", "code": "bind_queue(queue='{{logs}}', exchange='{{fanout_logs}}')"}
                ]
            ),
            MethodInfo(
                name="publish_message",
                description="Publish message to exchange with routing key",
                parameters={
                    "exchange": "str (required) - Exchange name (empty for default)",
                    "routing_key": "str (required) - Routing key",
                    "message": "str/dict/bytes (required) - Message body (dict auto-serialized to JSON)",
                    "properties": "dict (optional) - Message properties (content_type, delivery_mode, etc.)",
                    "mandatory": "bool (optional) - Must be routable (default False)"
                },
                returns="None",
                examples=[
                    {"text": "Publish message exchange {{tasks}} routing_key {{task.process}} message {{{'task': 'process'}}}", "code": "publish_message(exchange='{{tasks}}', routing_key='task.process', message={'task': 'process'})"},
                    {"text": "Publish message exchange {{}} routing_key {{my_queue}} message {{Hello}}", "code": "publish_message(exchange='', routing_key='{{my_queue}}', message='Hello')"}
                ]
            ),
            MethodInfo(
                name="consume_messages",
                description="Start consuming messages from queue (blocking)",
                parameters={
                    "queue": "str (required) - Queue name",
                    "callback": "function (required) - Callback(ch, method, properties, body)",
                    "auto_ack": "bool (optional) - Auto-acknowledge messages (default False)",
                    "prefetch_count": "int (optional) - Messages to prefetch (default 1)"
                },
                returns="None (blocks until Ctrl+C)",
                examples=[
                    {"text": "Consume messages queue {{tasks}} callback {{process_task}}", "code": "consume_messages(queue='{{tasks}}', callback={{process_task}})"}
                ]
            ),
            MethodInfo(
                name="get_message",
                description="Get single message from queue (non-blocking)",
                parameters={
                    "queue": "str (required) - Queue name",
                    "auto_ack": "bool (optional) - Auto-acknowledge (default False)"
                },
                returns="tuple - (method, properties, body) or (None, None, None)",
                examples=[
                    {"text": "Get message from queue {{tasks}}", "code": "get_message(queue='{{tasks}}')"}
                ]
            ),
            MethodInfo(
                name="purge_queue",
                description="Delete all messages from queue",
                parameters={"queue": "str (required) - Queue name"},
                returns="None",
                examples=[
                    {"text": "Purge queue {{old_tasks}}", "code": "purge_queue(queue='{{old_tasks}}')"}
                ]
            ),
            MethodInfo(
                name="delete_queue",
                description="Delete a queue",
                parameters={
                    "queue": "str (required) - Queue name",
                    "if_unused": "bool (optional) - Only if no consumers (default False)",
                    "if_empty": "bool (optional) - Only if empty (default False)"
                },
                returns="None",
                examples=[
                    {"text": "Delete queue {{temp_queue}}", "code": "delete_queue(queue='{{temp_queue}}')"}
                ]
            )
        ]

