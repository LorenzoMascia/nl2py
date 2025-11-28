# Contributing to NL2PyFlow

Thank you for your interest in contributing to NL2PyFlow! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## Getting Started

1. **Fork the Repository**
   ```bash
   git clone https://github.com/LorenzoMascia/NL2PyFlow.git
   cd NL2PyFlow
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

1. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -e ".[dev]"
   # Or using requirements files:
   pip install -r requirements-dev.txt
   ```

3. **Set Up Pre-commit Hooks** (Optional but recommended)
   ```bash
   pre-commit install
   ```

## How to Contribute

### Reporting Bugs

- Use the [GitHub Issues](https://github.com/LorenzoMascia/NL2PyFlow/issues) page
- Include a clear description of the bug
- Provide steps to reproduce
- Include your Python version and OS
- Add relevant code snippets or error messages

### Suggesting Features

- Open an issue with the tag `enhancement`
- Describe the feature and its use case
- Explain why it would be valuable

### Code Contributions

1. **Find or Create an Issue**
   - Check existing issues or create a new one
   - Comment on the issue to let others know you're working on it

2. **Write Code**
   - Follow the coding standards below
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   - Run the test suite
   - Ensure all tests pass
   - Add new tests if applicable

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use [Black](https://github.com/psf/black) for code formatting (line length: 100)
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use type hints where appropriate

### Code Formatting

```bash
# Format code with Black
black nl2pyflow tests

# Sort imports with isort
isort nl2pyflow tests

# Check code style with flake8
flake8 nl2pyflow tests
```

### Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstrings
- Update README.md if adding new features

Example:
```python
def parse_blocks(text: str) -> list[dict]:
    """
    Parse natural language text into block definitions.

    Args:
        text: Input text containing block definitions.

    Returns:
        List of dictionaries containing block information.

    Raises:
        ValueError: If text format is invalid.
    """
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nl2pyflow

# Run specific test file
pytest tests/test_block_parser.py
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files as `test_*.py`
- Use descriptive test function names

Example:
```python
def test_parse_blocks_with_valid_input():
    """Test that valid input is parsed correctly."""
    text = "### Block 1: Test\nDo something"
    blocks = parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0]['name'] == 'block_1'
```

## Submitting Changes

1. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

   Commit message format:
   - Use present tense ("Add feature" not "Added feature")
   - First line: brief summary (50 chars or less)
   - Blank line, then detailed description if needed

2. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template
   - Link related issues

### Pull Request Guidelines

- **Title**: Clear and descriptive
- **Description**:
  - What changes were made
  - Why the changes were necessary
  - How to test the changes
- **Tests**: Include tests for new features
- **Documentation**: Update docs if needed
- **Code Quality**: Ensure all checks pass

### PR Checklist

- [ ] Code follows the project's style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] All CI checks passing

## Development Tools

### Useful Commands

```bash
# Install package in development mode
pip install -e .

# Run the CLI locally
python -m nl2pyflow examples/basic_pipeline.txt

# Type checking with mypy
mypy nl2pyflow

# Generate coverage report
pytest --cov=nl2pyflow --cov-report=html
```

## Project Structure

```
NL2PyFlow/
├── nl2pyflow/           # Main package
│   ├── __init__.py      # Package initialization
│   ├── cli.py           # Command-line interface
│   ├── block_parser.py  # Block parsing logic
│   ├── code_generator.py # Code generation
│   ├── orchestrator.py  # Pipeline orchestration
│   ├── llm_handler.py   # LLM integration
│   ├── backend/         # Web backend
│   └── frontend/        # Web frontend
├── tests/               # Test suite
├── examples/            # Example files
├── docs/                # Documentation
├── pyproject.toml       # Project configuration
└── README.md            # Project overview
```

## Questions?

If you have questions, feel free to:
- Open an issue
- Start a discussion on GitHub Discussions
- Reach out to the maintainers

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing to NL2PyFlow! 🎉
