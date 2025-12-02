"""
MQTT (Message Queuing Telemetry Transport) Module for NL2Py

This module provides comprehensive MQTT messaging capabilities including:
- Broker Connection: Connect to MQTT brokers with authentication
- Publish Messages: Send messages to topics
- Subscribe to Topics: Receive messages from topics
- QoS Support: Quality of Service levels 0, 1, 2
- Retained Messages: Store last message on broker
- Last Will and Testament: Automatic disconnect messages
- TLS/SSL Support: Secure connections
- Callback Handlers: Custom message handlers

Configuration in nl2py.conf:
    [mqtt]
    BROKER = mqtt.example.com
    PORT = 1883
    USERNAME = mqtt_user
    PASSWORD = mqtt_password
    CLIENT_ID = aibasic_client
    KEEPALIVE = 60
    USE_TLS = false
    QOS = 1
"""

import os
import threading
import time
from typing import Dict, Any, Optional, Callable, List
import json
from .module_base import NL2PyModuleBase

try:
    import paho.mqtt.client as mqtt
except ImportError:
    raise ImportError(
        "MQTT module requires paho-mqtt. "
        "Install with: pip install paho-mqtt"
    )


class MQTTModule(NL2PyModuleBase):
    """
    MQTT module for IoT and pub/sub messaging.

    Implements singleton pattern for efficient resource usage.
    Provides comprehensive MQTT operations through paho-mqtt library.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MQTT module with configuration.

        Args:
            config: Configuration dictionary from nl2py.conf
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self.config = config or {}

            # Broker settings
            self.broker = self.config.get('BROKER') or os.getenv('MQTT_BROKER', 'localhost')
            self.port = int(self.config.get('PORT') or os.getenv('MQTT_PORT', '1883'))

            # Authentication
            self.username = self.config.get('USERNAME') or os.getenv('MQTT_USERNAME')
            self.password = self.config.get('PASSWORD') or os.getenv('MQTT_PASSWORD')

            # Client settings
            self.client_id = self.config.get('CLIENT_ID') or os.getenv('MQTT_CLIENT_ID', f'aibasic_{int(time.time())}')
            self.keepalive = int(self.config.get('KEEPALIVE') or os.getenv('MQTT_KEEPALIVE', '60'))
            self.clean_session = self.config.get('CLEAN_SESSION', 'true').lower() == 'true'

            # QoS (Quality of Service)
            self.default_qos = int(self.config.get('QOS') or os.getenv('MQTT_QOS', '1'))

            # TLS/SSL settings
            self.use_tls = self.config.get('USE_TLS', 'false').lower() == 'true'
            self.ca_certs = self.config.get('CA_CERTS') or os.getenv('MQTT_CA_CERTS')
            self.certfile = self.config.get('CERTFILE') or os.getenv('MQTT_CERTFILE')
            self.keyfile = self.config.get('KEYFILE') or os.getenv('MQTT_KEYFILE')

            # Last Will and Testament
            self.lwt_topic = self.config.get('LWT_TOPIC') or os.getenv('MQTT_LWT_TOPIC')
            self.lwt_payload = self.config.get('LWT_PAYLOAD') or os.getenv('MQTT_LWT_PAYLOAD', 'offline')
            self.lwt_qos = int(self.config.get('LWT_QOS') or os.getenv('MQTT_LWT_QOS', '1'))
            self.lwt_retain = self.config.get('LWT_RETAIN', 'false').lower() == 'true'

            # Client instance (lazy-loaded)
            self._client = None
            self._connected = False
            self._subscriptions = {}
            self._message_callbacks = {}

            self._initialized = True

    @property
    def client(self):
        """Get MQTT client (lazy-loaded)."""
        if self._client is None:
            try:
                # Create client
                self._client = mqtt.Client(
                    client_id=self.client_id,
                    clean_session=self.clean_session,
                    protocol=mqtt.MQTTv311
                )

                # Set callbacks
                self._client.on_connect = self._on_connect
                self._client.on_disconnect = self._on_disconnect
                self._client.on_message = self._on_message
                self._client.on_publish = self._on_publish
                self._client.on_subscribe = self._on_subscribe

                # Set authentication
                if self.username and self.password:
                    self._client.username_pw_set(self.username, self.password)

                # Set Last Will and Testament
                if self.lwt_topic:
                    self._client.will_set(
                        self.lwt_topic,
                        payload=self.lwt_payload,
                        qos=self.lwt_qos,
                        retain=self.lwt_retain
                    )

                # Configure TLS/SSL
                if self.use_tls:
                    self._client.tls_set(
                        ca_certs=self.ca_certs,
                        certfile=self.certfile,
                        keyfile=self.keyfile
                    )

            except Exception as e:
                raise RuntimeError(f"Failed to create MQTT client: {e}")

        return self._client

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when client connects to broker."""
        if rc == 0:
            self._connected = True
            print(f"Connected to MQTT broker: {self.broker}:{self.port}")

            # Resubscribe to topics after reconnection
            for topic, qos in self._subscriptions.items():
                client.subscribe(topic, qos)
        else:
            self._connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            error_msg = error_messages.get(rc, f"Connection failed with code {rc}")
            print(f"MQTT connection failed: {error_msg}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when client disconnects from broker."""
        self._connected = False
        if rc != 0:
            print(f"Unexpected disconnection from MQTT broker (code {rc})")

    def _on_message(self, client, userdata, message):
        """Callback when message is received."""
        topic = message.topic
        payload = message.payload.decode('utf-8')

        # Call custom callback if registered for this topic
        if topic in self._message_callbacks:
            callback = self._message_callbacks[topic]
            callback(topic, payload)
        else:
            print(f"Received message on topic '{topic}': {payload}")

    def _on_publish(self, client, userdata, mid):
        """Callback when message is published."""
        pass  # Can be extended for publish confirmation tracking

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when subscription is confirmed."""
        pass  # Can be extended for subscription confirmation tracking

    def connect(self, broker: Optional[str] = None, port: Optional[int] = None):
        """
        Connect to MQTT broker.

        Args:
            broker: MQTT broker hostname (optional, uses config if not provided)
            port: MQTT broker port (optional, uses config if not provided)
        """
        try:
            broker = broker or self.broker
            port = port or self.port

            self.client.connect(broker, port, self.keepalive)
            self.client.loop_start()

            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self._connected:
                raise RuntimeError("Connection timeout")

        except Exception as e:
            raise RuntimeError(f"Failed to connect to MQTT broker: {e}")

    def disconnect(self):
        """Disconnect from MQTT broker."""
        try:
            if self._client and self._connected:
                self.client.loop_stop()
                self.client.disconnect()
                self._connected = False
        except Exception as e:
            raise RuntimeError(f"Failed to disconnect from MQTT broker: {e}")

    def publish(self, topic: str, payload: str, qos: Optional[int] = None, retain: bool = False):
        """
        Publish message to topic.

        Args:
            topic: Topic to publish to
            payload: Message payload (will be converted to string)
            qos: Quality of Service (0, 1, or 2)
            retain: Whether broker should retain message
        """
        try:
            if not self._connected:
                self.connect()

            qos = qos if qos is not None else self.default_qos

            # Convert payload to string if needed
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            elif not isinstance(payload, str):
                payload = str(payload)

            result = self.client.publish(topic, payload, qos=qos, retain=retain)

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Publish failed with code {result.rc}")

            return result.mid

        except Exception as e:
            raise RuntimeError(f"Failed to publish message: {e}")

    def subscribe(self, topic: str, qos: Optional[int] = None, callback: Optional[Callable] = None):
        """
        Subscribe to topic.

        Args:
            topic: Topic to subscribe to (supports wildcards + and #)
            qos: Quality of Service (0, 1, or 2)
            callback: Optional callback function(topic, payload)
        """
        try:
            if not self._connected:
                self.connect()

            qos = qos if qos is not None else self.default_qos

            result = self.client.subscribe(topic, qos)

            if result[0] != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Subscribe failed with code {result[0]}")

            # Store subscription
            self._subscriptions[topic] = qos

            # Register callback if provided
            if callback:
                self._message_callbacks[topic] = callback

        except Exception as e:
            raise RuntimeError(f"Failed to subscribe to topic: {e}")

    def unsubscribe(self, topic: str):
        """
        Unsubscribe from topic.

        Args:
            topic: Topic to unsubscribe from
        """
        try:
            if not self._connected:
                raise RuntimeError("Not connected to MQTT broker")

            result = self.client.unsubscribe(topic)

            if result[0] != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Unsubscribe failed with code {result[0]}")

            # Remove subscription
            if topic in self._subscriptions:
                del self._subscriptions[topic]
            if topic in self._message_callbacks:
                del self._message_callbacks[topic]

        except Exception as e:
            raise RuntimeError(f"Failed to unsubscribe from topic: {e}")

    def publish_json(self, topic: str, data: Dict[str, Any], qos: Optional[int] = None, retain: bool = False):
        """
        Publish JSON data to topic.

        Args:
            topic: Topic to publish to
            data: Dictionary to serialize as JSON
            qos: Quality of Service (0, 1, or 2)
            retain: Whether broker should retain message
        """
        try:
            payload = json.dumps(data)
            return self.publish(topic, payload, qos, retain)
        except Exception as e:
            raise RuntimeError(f"Failed to publish JSON message: {e}")

    def wait_for_messages(self, timeout: Optional[int] = None):
        """
        Wait for incoming messages.

        Args:
            timeout: Timeout in seconds (None for indefinite)
        """
        try:
            if not self._connected:
                raise RuntimeError("Not connected to MQTT broker")

            if timeout:
                time.sleep(timeout)
            else:
                # Wait indefinitely
                while self._connected:
                    time.sleep(1)

        except KeyboardInterrupt:
            print("Message waiting interrupted")

    def is_connected(self) -> bool:
        """
        Check if client is connected to broker.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    def get_subscriptions(self) -> Dict[str, int]:
        """
        Get current subscriptions.

        Returns:
            Dictionary of topic: qos pairs
        """
        return self._subscriptions.copy()

    def set_last_will(self, topic: str, payload: str, qos: int = 1, retain: bool = False):
        """
        Set Last Will and Testament message.
        Must be called before connecting.

        Args:
            topic: LWT topic
            payload: LWT message
            qos: LWT QoS
            retain: Whether to retain LWT message
        """
        if self._connected:
            raise RuntimeError("Cannot set LWT while connected. Disconnect first.")

        self.lwt_topic = topic
        self.lwt_payload = payload
        self.lwt_qos = qos
        self.lwt_retain = retain

        # Update client if already created
        if self._client:
            self._client.will_set(topic, payload, qos, retain)

    def publish_retained(self, topic: str, payload: str, qos: Optional[int] = None):
        """
        Publish retained message (shorthand for publish with retain=True).

        Args:
            topic: Topic to publish to
            payload: Message payload
            qos: Quality of Service
        """
        return self.publish(topic, payload, qos, retain=True)

    def clear_retained(self, topic: str):
        """
        Clear retained message on topic by publishing empty payload.

        Args:
            topic: Topic to clear
        """
        return self.publish(topic, "", retain=True)

    def close(self):
        """Close MQTT connection and cleanup resources."""
        self.disconnect()
        self._client = None
        self._subscriptions.clear()
        self._message_callbacks.clear()

    # ========================================
    # Metadata methods for NL2Py compiler
    # ========================================

    @classmethod
    def get_metadata(cls):
        """Get module metadata for compiler prompt generation."""
        from nl2py.modules.module_base import ModuleMetadata
        return ModuleMetadata(
            name="MQTT",
            task_type="mqtt",
            description="MQTT (Message Queuing Telemetry Transport) IoT messaging protocol for publish/subscribe communication with QoS support",
            version="1.0.0",
            keywords=[
                "mqtt", "messaging", "iot", "pubsub", "publish", "subscribe",
                "broker", "qos", "retained", "lwt", "telemetry", "sensor", "device"
            ],
            dependencies=["paho-mqtt>=1.6.0"]
        )

    @classmethod
    def get_usage_notes(cls):
        """Get detailed usage notes for this module."""
        return [
            "Module uses singleton pattern via from_config() - one instance per application",
            "Supports MQTT protocol versions 3.1 and 3.1.1 via paho-mqtt library",
            "Provides three Quality of Service (QoS) levels: 0 (at most once), 1 (at least once), 2 (exactly once)",
            "Default QoS level is 1 unless configured otherwise in nl2py.conf",
            "Auto-reconnection with subscription persistence - subscriptions restored after disconnect",
            "Supports retained messages - broker stores last message for new subscribers",
            "Last Will and Testament (LWT) - automatic message on unexpected disconnect",
            "TLS/SSL encryption support with CA certificates, client certificates, and private keys",
            "Topic wildcards supported: '+' for single level, '#' for multi-level",
            "Supports both username/password authentication and anonymous connections",
            "Client ID can be auto-generated or specified for persistent sessions",
            "Clean session mode configurable - determines if broker stores subscriptions",
            "Keepalive interval configurable (default 60 seconds) for connection monitoring",
            "Custom message callbacks per topic for application-specific handling",
            "Background network loop manages automatic reconnection and message delivery",
            "JSON publishing convenience method for structured data",
            "Connection timeout is 10 seconds - raises error if broker unreachable",
            "All methods raise RuntimeError on failure with descriptive messages",
            "Use connect() before publishing if not auto-connected, or publish will auto-connect",
            "Disconnect and close() should be called to properly cleanup resources"
        ]

    @classmethod
    def get_methods_info(cls):
        """Get information about all methods in this module."""
        from nl2py.modules.module_base import MethodInfo
        return [
            MethodInfo(
                name="connect",
                description="Establish connection to MQTT broker with optional broker and port override",
                parameters={
                    "broker": "str (optional) - MQTT broker hostname or IP address (uses config if not provided)",
                    "port": "int (optional) - MQTT broker port, typically 1883 for plain or 8883 for TLS (uses config if not provided)"
                },
                returns="None - raises RuntimeError if connection fails or times out (10 second timeout)",
                examples=[
                    {"text": "Connect broker {{mqtt.example.com}}", "code": "connect(broker='{{mqtt.example.com}}')"},
                    {"text": "Connect broker {{192.168.1.100}} port {{1883}}", "code": "connect(broker='{{192.168.1.100}}', port={{1883}})"},
                    {"text": "Connect broker {{test.mosquitto.org}} port {{1883}}", "code": "connect(broker='{{test.mosquitto.org}}', port={{1883}})"}
                ]
            ),
            MethodInfo(
                name="disconnect",
                description="Gracefully disconnect from MQTT broker, stop network loop, and cleanup connection",
                parameters={},
                returns="None - raises RuntimeError on disconnect failure",
                examples=[
                    {"text": "Disconnect from MQTT broker", "code": "disconnect()"},
                    {"text": "Disconnect and stop network loop", "code": "disconnect()"}
                ]
            ),
            MethodInfo(
                name="publish",
                description="Publish message to MQTT topic with configurable QoS and retain flag",
                parameters={
                    "topic": "str (required) - MQTT topic to publish to (e.g., 'sensors/temperature')",
                    "payload": "str|dict (required) - Message payload, automatically JSON-encoded if dict",
                    "qos": "int (optional) - Quality of Service: 0, 1, or 2 (uses default_qos if not specified)",
                    "retain": "bool (optional) - Whether broker should retain message for new subscribers (default False)"
                },
                returns="int - Message ID for tracking publish confirmation",
                examples=[
                    {"text": "Publish topic {{test/messages}} payload {{hello world}}", "code": "publish(topic='{{test/messages}}', payload='{{hello world}}')"},
                    {"text": "Publish topic {{sensors/temp1}} payload {{temperature 25.5C}} qos {{2}}", "code": "publish(topic='{{sensors/temp1}}', payload='{{temperature 25.5C}}', qos={{2}})"},
                    {"text": "Publish topic {{sensors/data}} payload {{{'temp': 25.5, 'unit': 'C'}}} qos {{1}} retain {{True}}", "code": "publish(topic='{{sensors/data}}', payload={{'{{temp}}': {{25.5}}, '{{unit}}': '{{C}}'}}, qos={{1}}, retain={{True}})"}
                ]
            ),
            MethodInfo(
                name="subscribe",
                description="Subscribe to MQTT topic with optional QoS and custom message callback handler",
                parameters={
                    "topic": "str (required) - Topic to subscribe to, supports wildcards + and # (e.g., 'sensors/+/temperature')",
                    "qos": "int (optional) - Quality of Service: 0, 1, or 2 (uses default_qos if not specified)",
                    "callback": "function (optional) - Callback function(topic, payload) called when messages arrive"
                },
                returns="None - raises RuntimeError on subscription failure",
                examples=[
                    {"text": "Subscribe topic {{sensors/temperature}}", "code": "subscribe(topic='{{sensors/temperature}}')"},
                    {"text": "Subscribe topic {{devices/+/status}} qos {{1}}", "code": "subscribe(topic='{{devices/+/status}}', qos={{1}})"},
                    {"text": "Subscribe topic {{home/#}} qos {{2}}", "code": "subscribe(topic='{{home/#}}', qos={{2}})"}
                ]
            ),
            MethodInfo(
                name="unsubscribe",
                description="Unsubscribe from MQTT topic and remove associated callback handlers",
                parameters={
                    "topic": "str (required) - Topic to unsubscribe from"
                },
                returns="None - raises RuntimeError if not connected or unsubscribe fails",
                examples=[
                    {"text": "Unsubscribe topic {{sensors/temperature}}", "code": "unsubscribe(topic='{{sensors/temperature}}')"},
                    {"text": "Unsubscribe topic {{devices/+/status}}", "code": "unsubscribe(topic='{{devices/+/status}}')"}
                ]
            ),
            MethodInfo(
                name="publish_json",
                description="Publish Python dictionary as JSON-encoded message to topic with QoS and retain options",
                parameters={
                    "topic": "str (required) - MQTT topic to publish to",
                    "data": "dict (required) - Python dictionary to serialize as JSON",
                    "qos": "int (optional) - Quality of Service: 0, 1, or 2",
                    "retain": "bool (optional) - Whether broker should retain message"
                },
                returns="int - Message ID for tracking",
                examples=[
                    {"text": "Publish JSON topic {{sensors/data}} data {{{'sensor': 'temp1', 'value': 25.5}}}", "code": "publish_json(topic='{{sensors/data}}', data={{'{{sensor}}': '{{temp1}}', '{{value}}': {{25.5}}}})"},
                    {"text": "Publish JSON topic {{device/status}} data {{{'status': 'online', 'timestamp': 1234567890}}} qos {{1}} retain {{True}}", "code": "publish_json(topic='{{device/status}}', data={{'{{status}}': '{{online}}', '{{timestamp}}': {{1234567890}}}}, qos={{1}}, retain={{True}})"}
                ]
            ),
            MethodInfo(
                name="wait_for_messages",
                description="Block and wait for incoming messages on subscribed topics with optional timeout",
                parameters={
                    "timeout": "int (optional) - Timeout in seconds, None for indefinite wait"
                },
                returns="None - blocks until timeout or KeyboardInterrupt",
                examples=[
                    {"text": "Wait for messages timeout {{30}}", "code": "wait_for_messages(timeout={{30}})"},
                    {"text": "Wait for messages indefinitely", "code": "wait_for_messages()"}
                ]
            ),
            MethodInfo(
                name="is_connected",
                description="Check current connection status to MQTT broker",
                parameters={},
                returns="bool - True if connected, False otherwise",
                examples=[
                    {"text": "Check if connected to MQTT broker", "code": "is_connected()"},
                    {"text": "Get current connection status", "code": "is_connected()"}
                ]
            ),
            MethodInfo(
                name="get_subscriptions",
                description="Retrieve dictionary of all active topic subscriptions with their QoS levels",
                parameters={},
                returns="dict - Dictionary mapping topics to QoS levels (e.g., {'sensors/temp': 1, 'devices/+/status': 2})",
                examples=[
                    {"text": "Get current subscriptions dictionary", "code": "get_subscriptions()"},
                    {"text": "Get all active topic subscriptions", "code": "get_subscriptions()"}
                ]
            ),
            MethodInfo(
                name="set_last_will",
                description="Configure Last Will and Testament message sent by broker on unexpected client disconnect (must be called before connect)",
                parameters={
                    "topic": "str (required) - Topic for LWT message",
                    "payload": "str (required) - LWT message content",
                    "qos": "int (optional) - QoS for LWT (default 1)",
                    "retain": "bool (optional) - Whether to retain LWT message (default False)"
                },
                returns="None - raises RuntimeError if already connected",
                examples=[
                    {"text": "Set last will topic {{device/status}} payload {{offline}} qos {{1}} retain {{True}}", "code": "set_last_will(topic='{{device/status}}', payload='{{offline}}', qos={{1}}, retain={{True}})"},
                    {"text": "Set last will topic {{sensors/disconnect}} payload {{sensor offline}}", "code": "set_last_will(topic='{{sensors/disconnect}}', payload='{{sensor offline}}')"}
                ]
            ),
            MethodInfo(
                name="publish_retained",
                description="Publish message with retain flag set to True (shorthand for publish with retain=True)",
                parameters={
                    "topic": "str (required) - MQTT topic",
                    "payload": "str (required) - Message payload",
                    "qos": "int (optional) - Quality of Service"
                },
                returns="int - Message ID",
                examples=[
                    {"text": "Publish retained topic {{status/device1}} payload {{device online}}", "code": "publish_retained(topic='{{status/device1}}', payload='{{device online}}')"},
                    {"text": "Publish retained topic {{sensors/temp1}} payload {{25.5}} qos {{2}}", "code": "publish_retained(topic='{{sensors/temp1}}', payload='{{25.5}}', qos={{2}})"}
                ]
            ),
            MethodInfo(
                name="clear_retained",
                description="Clear retained message on topic by publishing empty payload with retain flag",
                parameters={
                    "topic": "str (required) - Topic to clear retained message from"
                },
                returns="int - Message ID",
                examples=[
                    {"text": "Clear retained topic {{sensors/temp1}}", "code": "clear_retained(topic='{{sensors/temp1}}')"},
                    {"text": "Clear retained topic {{status/device1}}", "code": "clear_retained(topic='{{status/device1}}')"}
                ]
            ),
            MethodInfo(
                name="close",
                description="Disconnect from broker and cleanup all resources, subscriptions, and callbacks",
                parameters={},
                returns="None",
                examples=[
                    {"text": "Close MQTT connection and cleanup", "code": "close()"},
                    {"text": "Close and cleanup all MQTT resources", "code": "close()"}
                ]
            )
        ]

# Module metadata
__all__ = ['MQTTModule']
