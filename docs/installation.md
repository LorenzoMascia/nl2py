# Installation Guide

## Requirements

- Python 3.10 or higher
- pip package manager
- OpenAI API key

## Installation Methods

### From PyPI (Recommended, when available)

```bash
pip install nl2pyflow
```

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/LorenzoMascia/NL2PyFlow.git
   cd NL2PyFlow
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

3. For development with all dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Configuration

### Setting up OpenAI API Key

You need to set your OpenAI API key as an environment variable:

**Linux/macOS:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

**Permanent Setup (.env file):**

Create a `.env` file in your project directory:
```
OPENAI_API_KEY=your-api-key-here
```

## Verification

Verify your installation:

```bash
nl2pyflow --help
```

Or in Python:

```python
import nl2pyflow
print(nl2pyflow.__version__)
```

## Next Steps

- Read the [Getting Started](getting-started.md) guide
- Check out [Examples](examples.md)
- Read the [API Reference](api-reference.md)
