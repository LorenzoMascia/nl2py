# Contributing to NL2Py

Thank you for your interest in contributing to NL2Py! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/lorenzomascia/nl2py/issues)
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected behavior vs actual behavior
   - Your environment (Python version, OS, etc.)
   - Any relevant error messages or logs

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with the `enhancement` label
3. Describe the feature and its use case
4. Explain why it would be valuable

### Pull Requests

1. Fork the repository
2. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Write or update tests as needed
5. Ensure all tests pass
6. Commit with clear messages
7. Push and create a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/lorenzomascia/nl2py.git
cd nl2py

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install dev dependencies
pip install pytest black ruff mypy

# Install optional GUI dependencies
pip install gradio>=4.0.0
```

## Project Structure

```
nl2py/
├── src/nl2py/
│   ├── nlp_interpreter.py    # Core NLP engine
│   ├── gui/                  # Gradio web interface
│   └── modules/              # Service modules
├── tests/                    # Test files
├── examples/                 # Example files
└── docker/                   # Docker setup
```

## Adding a New Module

### 1. Create the Module File

Create `src/nl2py/modules/myservice_module.py`:

```python
"""
MyService Module for NL2Py

Provides integration with MyService for doing useful things.
"""

from typing import Dict, List, Any, Optional
from nl2py.modules.module_base import (
    AIbasicModuleBase,
    ModuleMetadata,
    MethodInfo
)


class MyServiceModule(AIbasicModuleBase):
    """Module for MyService operations."""

    _instance = None  # Singleton pattern

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, api_key: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.api_key = api_key
        self._initialized = True

    @classmethod
    def get_metadata(cls) -> ModuleMetadata:
        return ModuleMetadata(
            name="MyService Module",
            task_type="myservice",
            description="Integration with MyService for doing useful things",
            version="1.0.0",
            keywords=["myservice", "integration", "api"],
            dependencies=["requests"]
        )

    @classmethod
    def get_usage_notes(cls) -> List[str]:
        return [
            "Requires API key via MYSERVICE_API_KEY environment variable",
            "Rate limited to 100 requests per minute",
            "All responses are cached for 5 minutes"
        ]

    @classmethod
    def get_methods_info(cls) -> List[MethodInfo]:
        return [
            MethodInfo(
                name="get_data",
                description="Retrieve data from MyService",
                parameters={
                    "resource_id": "ID of the resource to retrieve",
                    "format": "Output format (optional, default: 'json')"
                },
                returns="Dictionary with resource data",
                examples=[
                    {
                        "text": "get data for resource {{my-resource}}",
                        "code": "get_data(resource_id='{{my-resource}}')"
                    },
                    {
                        "text": "get data {{item-123}} in format {{xml}}",
                        "code": "get_data(resource_id='{{item-123}}', format='{{xml}}')"
                    }
                ]
            ),
            MethodInfo(
                name="create_resource",
                description="Create a new resource in MyService",
                parameters={
                    "name": "Name for the new resource",
                    "data": "Resource data as dictionary"
                },
                returns="Dictionary with created resource details",
                examples=[
                    {
                        "text": "create resource named {{my-new-resource}}",
                        "code": "create_resource(name='{{my-new-resource}}')"
                    }
                ]
            )
        ]

    def get_data(self, resource_id: str, format: str = "json") -> Dict[str, Any]:
        """Retrieve data from MyService."""
        # Implementation here
        return {"status": "success", "resource_id": resource_id}

    def create_resource(self, name: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a new resource."""
        # Implementation here
        return {"status": "created", "name": name}


# Module factory function
def get_myservice_module(api_key: Optional[str] = None) -> MyServiceModule:
    """Get or create MyServiceModule instance."""
    return MyServiceModule(api_key=api_key)
```

### 2. Register the Module

Add to `src/nl2py/modules/__init__.py`:

```python
_import_module('myservice_module', 'MyServiceModule')
```

### 3. Write Examples

The `examples` field in `MethodInfo` is crucial for NLP matching. Follow these patterns:

- Use `{{parameter}}` placeholders for variable parts
- Provide multiple examples with different phrasings
- Cover common use cases

```python
examples=[
    {"text": "get data for {{resource}}", "code": "get_data(resource_id='{{resource}}')"},
    {"text": "retrieve {{resource}} data", "code": "get_data(resource_id='{{resource}}')"},
    {"text": "fetch resource {{resource}}", "code": "get_data(resource_id='{{resource}}')"},
]
```

### 4. Add Tests

Create `tests/test_myservice_module.py`:

```python
import pytest
from nl2py.modules.myservice_module import MyServiceModule


class TestMyServiceModule:
    def test_get_metadata(self):
        metadata = MyServiceModule.get_metadata()
        assert metadata.name == "MyService Module"
        assert metadata.task_type == "myservice"

    def test_get_methods_info(self):
        methods = MyServiceModule.get_methods_info()
        assert len(methods) > 0
        assert methods[0].name == "get_data"

    def test_get_data(self):
        module = MyServiceModule()
        result = module.get_data("test-resource")
        assert result["status"] == "success"
```

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for public methods

```bash
# Format code
black src/ tests/

# Check linting
ruff check src/ tests/

# Type checking
mypy src/
```

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add MyService module with get_data and create_resource methods

- Implements singleton pattern
- Adds 5 NLP examples per method
- Includes unit tests
```

Prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `test:` - Tests
- `chore:` - Maintenance

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nl2py

# Run specific test file
pytest tests/test_myservice_module.py

# Run specific test
pytest tests/test_myservice_module.py::TestMyServiceModule::test_get_data
```

## Documentation

- Update README.md if adding new features
- Add docstrings to all public methods
- Update the module table in README.md when adding modules
- Include examples in method documentation

## Questions?

Feel free to open an issue for any questions about contributing.

Thank you for contributing to NL2Py!
