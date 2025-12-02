# Changelog

All notable changes to NL2Py will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of NL2Py
- Core NLP interpreter with TF-IDF similarity matching
- Gradio-based web GUI with multiple tabs
- CLI support for interactive and file processing modes
- 35+ service modules:
  - **Cloud**: AWS, GCP, Azure, Terraform
  - **Containers**: Docker, Kubernetes
  - **Databases**: PostgreSQL, MySQL, MongoDB, Redis, Cassandra, ScyllaDB, ClickHouse, Neo4j, Elasticsearch, OpenSearch, TimescaleDB
  - **Messaging**: Kafka, RabbitMQ, MQTT
  - **Communication**: Slack, Teams, Discord, Telegram, Email
  - **Security**: Vault, Keycloak, LDAP, JWT
  - **Storage**: S3
  - **Other**: SSH, Selenium, Prometheus, REST API, Compression
- Module base class with standardized interface
- Parameter extraction from natural language
- Docker Compose setup for local development services
- Configuration file support (`nl2py.conf`)

### Features
- Natural language to Python code translation
- Automatic parameter extraction using pattern matching
- Similarity-based method matching
- Web interface with:
  - Single command translation
  - Full text translation with Python script generation
  - Line-by-line analysis view
  - Method explorer
  - Methods reference browser
- Adjustable similarity threshold
- Optional comment inclusion in generated code

## [0.1.0] - 2024-11-03

### Added
- Initial public release

---

## Version History

### Versioning Scheme

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Upgrade Notes

#### Upgrading to 0.1.0
This is the initial release. No upgrade path required.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute to this project.
