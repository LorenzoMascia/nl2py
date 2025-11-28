# Getting Started

This guide will help you create your first NL2PyFlow pipeline.

## Basic Concepts

### Blocks

A block is a natural language description of a task. Each block is converted into a Python function.

### Context

The `context` is a Python dictionary that flows through all blocks, allowing them to share data.

### Pipeline

A pipeline is a sequence of blocks executed in order, each receiving and returning the shared context.

## Your First Pipeline

### 1. Create a Workflow File

Create a file called `my_workflow.txt`:

```markdown
### Block 1: Initialize
Create a list of numbers from 1 to 10 and store it in context["numbers"].

### Block 2: Square Numbers
Square each number in context["numbers"] and store the result in context["squared"].

### Block 3: Calculate Sum
Sum all squared numbers and store the total in context["total"].
```

### 2. Run the Pipeline

```bash
nl2pyflow my_workflow.txt
```

### 3. View the Results

The pipeline will:
1. Parse your blocks
2. Generate Python code for each block using an LLM
3. Execute the blocks in sequence
4. Display the final context

## Using as a Library

You can also use NL2PyFlow programmatically:

```python
from nl2pyflow import parse_blocks, generate_code_for_block, Orchestrator

# Read your workflow
with open("my_workflow.txt") as f:
    text = f.read()

# Parse blocks
blocks = parse_blocks(text)

# Generate code for each block
for block in blocks:
    generate_code_for_block(block, output_dir="blocks")

# Execute the pipeline
orchestrator = Orchestrator(blocks_dir="blocks")
result = orchestrator.run_pipeline([b['name'] for b in blocks])

print("Final result:", result)
```

## Advanced Usage

### Custom Output Directory

```bash
nl2pyflow my_workflow.txt --output-dir custom_blocks
```

### Web Interface

Start the web interface (if available):

```bash
python -m nl2pyflow.backend.app
```

Then open your browser to `http://localhost:5000`.

## Next Steps

- Explore more [Examples](examples.md)
- Read the [API Reference](api-reference.md)
- Learn about [Contributing](../CONTRIBUTING.md)
