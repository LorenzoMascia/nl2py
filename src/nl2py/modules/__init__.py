"""
NL2Py Modules

This package contains reusable modules that can be used by NL2Py programs.
Each module provides specific functionality (database connections, APIs, etc.)
and can be initialized from nl2py.conf configuration.

Note: Some modules may not be available if their dependencies are not installed.
Modules will be silently skipped if dependencies are missing.
"""

import importlib

# List of all available modules (will be populated as imports succeed)
__all__ = []

# Helper function to import modules with optional dependencies
def _import_module(module_name, class_name):
    """Import a module, handling missing dependencies gracefully."""
    try:
        module = importlib.import_module(f'.{module_name}', package='aibasic.modules')
        cls = getattr(module, class_name)
        globals()[class_name] = cls
        __all__.append(class_name)
        return cls
    except (ImportError, AttributeError) as e:
        # Module or dependency not available, skip silently
        return None

# Import all modules with optional dependency handling
_import_module('postgres_module', 'PostgresModule')
_import_module('mysql_module', 'MySQLModule')
_import_module('rabbitmq_module', 'RabbitMQModule')
_import_module('kafka_module', 'KafkaModule')
_import_module('redis_module', 'RedisModule')
_import_module('opensearch_module', 'OpenSearchModule')
_import_module('compression_module', 'CompressionModule')
_import_module('vault_module', 'VaultModule')
_import_module('cassandra_module', 'CassandraModule')
_import_module('email_module', 'EmailModule')
_import_module('mongodb_module', 'MongoDBModule')
_import_module('s3_module', 'S3Module')
_import_module('restapi_module', 'RestAPIModule')
_import_module('ssh_module', 'SSHModule')
_import_module('teams_module', 'TeamsModule')
_import_module('slack_module', 'SlackModule')
_import_module('clickhouse_module', 'ClickHouseModule')
_import_module('neo4j_module', 'Neo4jModule')
_import_module('elasticsearch_module', 'ElasticsearchModule')
_import_module('timescaledb_module', 'TimescaleDBModule')
_import_module('aws_module', 'AWSModule')
_import_module('terraform_module', 'TerraformModule')
_import_module('docker_module', 'DockerModule')
_import_module('kubernetes_module', 'KubernetesModule')
_import_module('azure_module', 'AzureModule')
_import_module('gcp_module', 'GCPModule')
_import_module('ldap_module', 'LDAPModule')
_import_module('keycloak_module', 'KeycloakModule')
_import_module('jwt_module', 'JWTModule')
_import_module('mqtt_module', 'MQTTModule')
_import_module('prometheus_module', 'PrometheusModule')
_import_module('scylladb_module', 'ScyllaDBModule')
_import_module('selenium_module', 'SeleniumModule')
_import_module('discord_module', 'DiscordModule')
_import_module('telegram_module', 'TelegramModule')
