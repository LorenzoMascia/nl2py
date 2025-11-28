# Examples

## Example 1: Data Processing Pipeline

Create a file `data_pipeline.txt`:

```markdown
### Block 1: Load Data
Load CSV file "sales.csv" into context["raw_data"] as a list of dictionaries.

### Block 2: Filter Data
Filter context["raw_data"] to include only records where amount > 1000, store in context["filtered_data"].

### Block 3: Calculate Statistics
Calculate the sum, average, min, and max of amounts in context["filtered_data"] and store in context["stats"].

### Block 4: Generate Report
Create a summary report string from context["stats"] and store in context["report"].
```

Run it:
```bash
nl2pyflow data_pipeline.txt
```

## Example 2: Text Processing

Create `text_processing.txt`:

```markdown
### Block 1: Load Text
Read text file "input.txt" and store content in context["text"].

### Block 2: Clean Text
Remove extra whitespace and convert to lowercase, store in context["cleaned_text"].

### Block 3: Count Words
Count word frequency and store top 10 most common words in context["word_counts"].

### Block 4: Extract Keywords
Extract keywords using simple heuristics and store in context["keywords"].
```

## Example 3: API Integration

Create `api_workflow.txt`:

```markdown
### Block 1: Fetch Data
Make GET request to "https://api.example.com/data" and store JSON response in context["api_data"].

### Block 2: Transform Data
Extract relevant fields from context["api_data"] and store in context["processed_data"].

### Block 3: Save Results
Save context["processed_data"] to JSON file "output.json".
```

## Example 4: Mathematical Operations

Create `math_pipeline.txt`:

```markdown
### Block 1: Generate Numbers
Create a list of 100 random numbers between 0 and 1000, store in context["numbers"].

### Block 2: Statistical Analysis
Calculate mean, median, and standard deviation, store in context["statistics"].

### Block 3: Create Bins
Divide numbers into 10 bins and count items per bin, store in context["histogram"].

### Block 4: Find Outliers
Identify numbers more than 2 standard deviations from mean, store in context["outliers"].
```

## Example 5: Using as a Library

```python
from nl2pyflow import parse_blocks, generate_code_for_block, Orchestrator
import os

# Set up your workflow
workflow = """
### Block 1: Initialize
Create a dictionary with keys 'a', 'b', 'c' and values 1, 2, 3 in context["data"].

### Block 2: Double Values
Double all values in context["data"] and store result in context["doubled"].

### Block 3: Sum Values
Sum all values in context["doubled"] and store in context["total"].
"""

# Parse blocks
blocks = parse_blocks(workflow)
print(f"Found {len(blocks)} blocks")

# Generate code
output_dir = "generated_blocks"
os.makedirs(output_dir, exist_ok=True)

block_names = []
for block in blocks:
    print(f"Generating code for {block['name']}")
    generate_code_for_block(block, output_dir=output_dir)
    block_names.append(block['name'])

# Execute pipeline
orchestrator = Orchestrator(blocks_dir=output_dir)
result = orchestrator.run_pipeline(block_names)

# Display results
print("\nFinal Context:")
for key, value in result.items():
    print(f"  {key}: {value}")
```

## Example 6: Custom Error Handling

```python
from nl2pyflow import parse_blocks, Orchestrator

try:
    # Read workflow
    with open("workflow.txt") as f:
        text = f.read()

    # Parse
    blocks = parse_blocks(text)

    # Execute with error handling
    orchestrator = Orchestrator()
    result = orchestrator.run_pipeline([b['name'] for b in blocks])

    print("Success!", result)

except FileNotFoundError:
    print("Workflow file not found")
except ValueError as e:
    print(f"Invalid workflow format: {e}")
except Exception as e:
    print(f"Pipeline execution failed: {e}")
```

## Tips for Writing Good Blocks

1. **Be Specific**: Clearly describe what data to read and where to store results
2. **Use Context**: Always reference the context dictionary for input/output
3. **Sequential Logic**: Each block should build on previous blocks
4. **Single Responsibility**: Keep each block focused on one task
5. **Clear Naming**: Use descriptive titles for blocks

## More Examples

Check the `examples/` directory in the repository for more sample workflows!
