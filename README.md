<div align="center">
  <img src="images/logo.svg" alt="NL2Py Logo" width="80" height="80">
  <h1>NL2Py - Natural Language to Python</h1>

  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
 
 <img width="756" height="712" alt="image" src="https://github.com/user-attachments/assets/ce770ca0-e189-423c-b5ff-a18b02fb0a6e" />

  <p><strong>NL2Py</strong> is a natural language to Python code compiler. Write commands in plain English and get executable Python code that interacts with cloud services, databases, APIs, and more.</p>
</div>

## Features

- **Natural Language Processing** - TF-IDF based similarity matching to find the right method
- **35+ Service Modules** - AWS, GCP, Azure, Kubernetes, Docker, databases, messaging, and more
- **Parameter Extraction** - Automatically extracts parameters from your natural language commands
- **Web GUI** - Gradio-based interface for interactive translation
- **CLI Support** - Process files or use interactive mode from the terminal
- **Extensible** - Easy to add new modules following the standard interface

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/lorenzomascia/nl2py.git
cd nl2py

# Install in development mode
pip install -e .

# Install GUI dependencies (optional)
pip install gradio>=4.0.0
```

### Usage

#### Web GUI

```bash
# Launch the web interface
nl2py-gui

# Or with Python
python -m nl2py.gui.nlp_gui
```

The GUI opens at `http://localhost:7860` with tabs for:
- **Single Command** - Translate one command at a time
- **Full Translation** - Convert multiple lines to a complete Python script
- **Line-by-Line Analysis** - See match details for each line
- **Explore Matches** - Find alternative methods for a command
- **Methods Reference** - Browse all available methods

<!-- Uncomment and add your GUI screenshot here -->
<!-- ![NL2Py GUI](images/gui-screenshot.png) -->

#### CLI

```bash
# Interactive mode
python -m nl2py.nlp_interpreter --interactive

# Process a file
python -m nl2py.nlp_interpreter commands.txt output.py
```

#### Python API

```python
from nl2py import create_interpreter

# Create and initialize the interpreter
interpreter = create_interpreter()

# Translate a command
result = interpreter.interpret("create compute instance web-server in zone us-central1-a")

print(result.generated_code)
# Output: compute_instance_create(name='web-server', zone='us-central1-a')

print(result.module_name)    # GCPModule
print(result.method_name)    # compute_instance_create
print(result.similarity_score)  # 0.85
```

## Example Commands

```text
# Cloud Infrastructure
create compute instance web-server in zone us-central1-a
create s3 bucket my-backup-bucket in region eu-west-1
list all docker containers

# Databases
connect to postgres database mydb
execute query "SELECT * FROM users"
set redis key user:123 with value "John Doe"

# Messaging
send message to slack channel general with text "Deploy completed"
send email to admin@example.com with subject "Alert"
publish message to kafka topic orders
```

## Available Modules

| Category | Modules |
|----------|---------|
| **Cloud** | AWS, GCP, Azure, Terraform |
| **Containers** | Docker, Kubernetes |
| **Databases** | PostgreSQL, MySQL, MongoDB, Redis, Cassandra, ScyllaDB, ClickHouse, Neo4j, Elasticsearch, OpenSearch, TimescaleDB |
| **Messaging** | Kafka, RabbitMQ, MQTT, Pub/Sub |
| **Communication** | Slack, Teams, Discord, Telegram, Email |
| **Security** | Vault, Keycloak, LDAP, JWT |
| **Storage** | S3, Cloud Storage |
| **Other** | SSH, Selenium, Prometheus, REST API, Compression |

## Configuration

Create a `nl2py.conf` file (see `nl2py.conf.example`) to configure module credentials:

```ini
[postgres]
host = localhost
port = 5432
database = mydb
user = postgres
password = secret

[aws]
region = us-east-1
access_key_id = AKIA...
secret_access_key = ...

[slack]
webhook_url = https://hooks.slack.com/services/...
```

## Project Structure

```
nl2py/
├── src/nl2py/
│   ├── __init__.py
│   ├── nlp_interpreter.py    # Core NLP engine
│   ├── gui/
│   │   ├── __init__.py
│   │   └── nlp_gui.py        # Gradio web interface
│   └── modules/
│       ├── module_base.py    # Base class and interfaces
│       ├── aws_module.py
│       ├── gcp_module.py
│       ├── postgres_module.py
│       └── ...               # 35+ modules
├── examples/
│   └── nlp_commands.txt      # Example commands
├── docker/                   # Docker setup for services
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Adding a New Module

1. Create a new file in `src/nl2py/modules/`
2. Inherit from `AIbasicModuleBase` (or implement the interface)
3. Implement required methods:

```python
from nl2py.modules.module_base import AIbasicModuleBase, ModuleMetadata, MethodInfo

class MyModule(AIbasicModuleBase):
    @classmethod
    def get_metadata(cls):
        return ModuleMetadata(
            name="My Module",
            task_type="my_task",
            description="Does something useful",
            keywords=["my", "module"]
        )

    @classmethod
    def get_methods_info(cls):
        return [
            MethodInfo(
                name="do_something",
                description="Does something with a parameter",
                parameters={"param": "The parameter to use"},
                returns="Result of the operation",
                examples=[
                    {"text": "do something with {{value}}",
                     "code": "do_something(param='{{value}}')"}
                ]
            )
        ]

    def do_something(self, param: str):
        # Implementation
        pass
```

4. Register in `src/nl2py/modules/__init__.py`

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/

# Format code
black src/
```

## Docker Services

For local development with databases and services:

```bash
cd docker
docker-compose up -d

# Services available:
# - PostgreSQL: localhost:5432
# - MySQL: localhost:3306
# - Redis: localhost:6379
# - MongoDB: localhost:27017
# - And more...
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Gradio](https://gradio.app/) for the web interface
- Uses TF-IDF similarity for natural language matching
- Inspired by the need to simplify cloud and infrastructure automation
