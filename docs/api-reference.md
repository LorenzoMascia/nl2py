# API Reference

## Core Modules

### nl2pyflow.block_parser

#### `parse_blocks(text: str) -> list[dict]`

Parse natural language text into block definitions.

**Parameters:**
- `text` (str): Input text containing block definitions in markdown format

**Returns:**
- list[dict]: List of block dictionaries with keys: `name`, `title`, `description`

**Example:**
```python
from nl2pyflow import parse_blocks

text = """
### Block 1: Load Data
Load CSV file into context.
"""

blocks = parse_blocks(text)
print(blocks[0]['name'])  # "block_1"
```

---

### nl2pyflow.code_generator

#### `generate_code_for_block(block: dict, output_dir: str = "blocks") -> str`

Generate Python code for a block using an LLM.

**Parameters:**
- `block` (dict): Block definition with `name`, `title`, and `description`
- `output_dir` (str): Directory to save generated code files

**Returns:**
- str: Path to the generated Python file

**Example:**
```python
from nl2pyflow import generate_code_for_block

block = {
    'name': 'block_1',
    'title': 'Load Data',
    'description': 'Load CSV into context["data"]'
}

file_path = generate_code_for_block(block, output_dir="blocks")
```

---

### nl2pyflow.orchestrator

#### `class Orchestrator`

Manages pipeline execution.

**Methods:**

##### `__init__(blocks_dir: str = "blocks")`

Initialize the orchestrator.

**Parameters:**
- `blocks_dir` (str): Directory containing generated block files

##### `run_pipeline(block_names: list[str]) -> dict`

Execute blocks in sequence.

**Parameters:**
- `block_names` (list[str]): List of block names to execute in order

**Returns:**
- dict: Final context after all blocks have executed

**Example:**
```python
from nl2pyflow import Orchestrator

orch = Orchestrator(blocks_dir="blocks")
result = orch.run_pipeline(["block_1", "block_2", "block_3"])
print(result)
```

---

### nl2pyflow.llm_handler

#### `class LLMHandler`

Handles communication with the LLM API.

**Methods:**

##### `generate_function(block_name: str, description: str) -> str`

Generate a Python function from a description.

**Parameters:**
- `block_name` (str): Name of the block/function
- `description` (str): Natural language description of what the function should do

**Returns:**
- str: Generated Python code

---

## Command-Line Interface

### nl2pyflow

Main CLI entry point.

**Usage:**
```bash
nl2pyflow [OPTIONS] INPUT_FILE
```

**Arguments:**
- `INPUT_FILE`: Path to file containing block definitions

**Options:**
- `--output-dir DIR`: Directory for generated files (default: "blocks")
- `--help`: Show help message

**Example:**
```bash
nl2pyflow workflow.txt --output-dir custom_blocks
```

---

## Type Hints

All functions include type hints for better IDE support and type checking:

```python
def parse_blocks(text: str) -> list[dict]: ...
def generate_code_for_block(block: dict, output_dir: str = "blocks") -> str: ...
```

## Error Handling

All functions may raise standard Python exceptions:

- `ValueError`: Invalid input format
- `FileNotFoundError`: Missing input file
- `RuntimeError`: Execution errors
- `Exception`: LLM API errors

Always wrap calls in try-except blocks for production use:

```python
try:
    blocks = parse_blocks(text)
except ValueError as e:
    print(f"Invalid block format: {e}")
```
