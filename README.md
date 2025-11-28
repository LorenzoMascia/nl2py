# NL2PyFlow

**Natural Language to Python Flow**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

![Screenshot 2025-04-28 181105](https://github.com/user-attachments/assets/39dcc333-a59f-4c40-8655-894cc174025c)

> A pipeline that converts high level natural language blocks into executable Python functions, chained together with a shared context.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Architecture](#architecture)
6. [Core Components](#core-components)
7. [Data Flow & Context Management](#data-flow--context-management)
8. [LLM Integration](#llm-integration)
9. [Example Workflow](#example-workflow)
10. [Development](#development)
11. [Future Extensions](#future-extensions)
12. [Contributing](#contributing)
13. [License](#license)

---

## Overview

NL2PyFlow enables users to author discrete, descriptive blocks in plain English or any other language. An LLM interprets each block and generates corresponding Python functions. An orchestrator then dynamically loads and executes these functions in sequence, sharing data via a unified `context` dictionary.

## Features

- **Natural Language Processing**: Write workflow steps in plain English
- **Automatic Code Generation**: LLM-powered Python function generation
- **Dynamic Pipeline Execution**: Runtime assembly and execution of generated code
- **Shared Context**: Seamless data flow between pipeline blocks
- **Web Interface**: Browser-based editor for creating and managing workflows
- **Extensible**: Easy to add custom blocks and extend functionality

## Installation

### From PyPI (when published)

```bash
pip install nl2pyflow
```

### From Source

```bash
# Clone the repository
git clone https://github.com/LorenzoMascia/NL2PyFlow.git
cd NL2PyFlow

# Install in development mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Requirements

- Python 3.10 or higher
- OpenAI API key (set as environment variable `OPENAI_API_KEY`)

## Quick Start

1. **Set up your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Create a workflow file** (e.g., `my_workflow.txt`):
   ```markdown
   ### Block 1: Load data
   Load CSV file "data.csv" into a list of records.

   ### Block 2: Process data
   Filter records where amount > 1000.

   ### Block 3: Calculate total
   Sum all amounts and store in context["total"].
   ```

3. **Run the pipeline**:
   ```bash
   nl2pyflow my_workflow.txt
   ```

4. **Or use as a Python library**:
   ```python
   from nl2pyflow import parse_blocks, generate_code_for_block, Orchestrator

   # Parse your workflow
   with open("my_workflow.txt") as f:
       blocks = parse_blocks(f.read())

   # Generate and execute
   orchestrator = Orchestrator()
   result = orchestrator.run_pipeline([b['name'] for b in blocks])
   print(result)
   ```

## Goals

- **Intuitive DSL**: Allow non‑programmers to define workflow steps in natural language.
- **Automated Code Generation**: Use an LLM to translate descriptions into Python functions with a standard signature.
- **Composable Pipeline**: Chain generated functions seamlessly, passing state through a shared `context`.
- **Runtime Execution**: Dynamically assemble and execute the full Python script without manual coding.

## Architecture

```mermaid
graph LR
  UI["User Interface"] --> Parser
  Parser --> LLM["LLM Code Generator"]
  LLM --> Generator["Function Generator"]
  Generator --> Filesystem[".py Modules"]
  Orchestrator --> Filesystem
  Orchestrator --> Execution["Run Functions"]
  Execution --> Context["Shared Context"]
```

1. **User Interface**: Editor or notebook for NL block definitions.
2. **Parser**: Splits text into ordered blocks and labels them (e.g., `block_1`).
3. **LLM Code Generator**: Prompts the LLM to generate each block as a Python function.
4. **Function Generator**: Validates, sanitizes, and writes the generated code to modules.
5. **Orchestrator**: Dynamically imports functions, initializes `context`, and executes each function sequentially.
6. **Context Store**: A Python `dict` carrying inputs, outputs, and intermediate data.

## Core Components

| Component                | Responsibility                                                       |
| ------------------------ | -------------------------------------------------------------------- |
| **Block Definition**     | Natural language descriptions, each as an independent workflow step. |
| **Parser**               | Identifies blocks and prepares prompts for the LLM.                  |
| **LLM Prompt Templates** | Standardizes prompt format and enforces function signature.          |
| **Function Generator**   | Calls the LLM, handles code validation, and writes `.py` files.      |
| **Orchestrator**         | Loads and runs generated functions, managing the shared `context`.   |
| **Error Handler**        | Logs exceptions, diagnostics, and optionally retries or aborts.      |

## Data Flow & Context Management

1. **Initialize**
   ```python
   context = {}
   ```
2. **Block Execution**
   ```python
   def block_n(context: dict) -> dict:
       # generated code
       context['key_n'] = value
       return context
   ```
3. **Chaining**
   - Each block reads and writes to the same `context` dict.
4. **Completion**
   - Final context contains all named outputs for user inspection.

## LLM Integration

**Prompt Template**:

```text
You are a Python expert. Generate a function based on the following description:

Block name: {block_name}
Description: "{block_description}"

Requirements:
- Signature: `def {block_name}(context: dict) -> dict`
- Read from and write to `context`
- Return updated `context`
```

**Validation**:

- Parse with `ast.parse` to ensure syntactic correctness.
- Optionally run unit tests or lint checks before execution.

## Example Workflow

**User Input**:

```markdown
### Block 1: Load data
Load CSV "sales.csv" into a list of records.

### Block 2: Filter high‑value
Filter records with amount > 1000.

### Block 3: Compute total
Sum all amounts and store in `context["total_sales"]`.
```

**Generated Code**:

![Screenshot 2025-04-28 181134](https://github.com/user-attachments/assets/8df9d6a5-bd58-4d56-a096-641ae75e15c3)

```python
# block_1.py
def block_1(context: dict) -> dict:
    import csv
    with open("sales.csv") as f:
        context["records"] = list(csv.DictReader(f))
    return context

# block_2.py
def block_2(context: dict) -> dict:
    context["filtered"] = [r for r in context["records"] if float(r["amount"]) > 1000]
    return context

# block_3.py
def block_3(context: dict) -> dict:
    context["total_sales"] = sum(float(r["amount"]) for r in context["filtered"])
    return context
```

**Orchestrator**:

```python
import importlib

def run_pipeline(block_names):
    context = {}
    for name in block_names:
        module = importlib.import_module(name)
        context = getattr(module, name)(context)
    return context

if __name__ == "__main__":
    result = run_pipeline(["block_1", "block_2", "block_3"])
    print(result)
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/LorenzoMascia/NL2PyFlow.git
cd NL2PyFlow

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
# Or: pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nl2pyflow --cov-report=html

# Run specific test file
pytest tests/test_block_parser.py
```

### Code Quality

```bash
# Format code
black nl2pyflow tests
isort nl2pyflow tests

# Lint code
flake8 nl2pyflow tests

# Type checking
mypy nl2pyflow
```

### Using Makefile

```bash
make install-dev  # Install dev dependencies
make test         # Run tests
make lint         # Run linters
make format       # Format code
make clean        # Clean build artifacts
make build        # Build package
```

## Technology Stack

- **Python**: 3.10+
- **LLM**: OpenAI GPT-4 (or equivalent) API
- **Dynamic Loader**: `importlib` or `exec`
- **Storage**: Local filesystem or database for code & logs
- **UI**: CLI, web editor, or Jupyter Notebook

## Future Extensions

- **Dependency Analysis**: Auto‑derive execution order based on context keys.
- **Parallel Execution**: Run independent blocks concurrently.
- **Version Control**: Track block revisions and enable rollbacks.
- **Schema Validation**: Enforce types in `context` with Pydantic.
- **Visual Debugger**: Interactive inspection of `context` state per block.

## Contributing

Contributions, issues, and feature requests are welcome! Please follow these steps:

1. Fork the repository
2. Create a branch (`git checkout -b feature/XYZ`)
3. Commit your changes (`git commit -m 'Add XYZ'`)
4. Push to the branch (`git push origin feature/XYZ`)
5. Open a Pull Request

## License

This project is licensed under the [Apache License 2.0](LICENSE).


