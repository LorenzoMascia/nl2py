"""Command-line interface for NL2PyFlow."""
import argparse
import os
from nl2pyflow.block_parser import parse_blocks
from nl2pyflow.code_generator import generate_code_for_block
from nl2pyflow.orchestrator import Orchestrator

def main():
    """
    Main entry point for NL2PyFlow.
    
    Parses command line arguments, reads input file, processes blocks, 
    generates code, and executes the pipeline.
    """
    parser = argparse.ArgumentParser(description="NL2PyFlow: Natural Language to Python Flow")
    parser.add_argument("input_file", help="Path to input file with block definitions")
    parser.add_argument("--output-dir", default="blocks", help="Directory to save generated block files")
    args = parser.parse_args()
    
    # Ensure the output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Read input file
    try:
        with open(args.input_file, "r") as f:
            nl_text = f.read()
    except Exception as e:
        print(f"Error reading input file: {str(e)}")
        return
    
    # Parse blocks
    print(f"Parsing input file: {args.input_file}")
    blocks = parse_blocks(nl_text)
    print(f"Found {len(blocks)} blocks")
    
    # Generate code for each block
    block_files = []
    for block in blocks:
        try:
            print(f"Generating code for {block['name']}: {block['title']}")
            file_path = generate_code_for_block(block, output_dir=args.output_dir)
            block_files.append(block['name'])
        except Exception as e:
            print(f"Error generating code for {block['name']}: {str(e)}")
            return
    
    # Execute the pipeline
    print("\nExecuting pipeline...")
    orchestrator = Orchestrator(blocks_dir=args.output_dir)
    
    try:
        final_context = orchestrator.run_pipeline(block_files)
        
        # Print the final context
        print("\nFinal context:")
        for key, value in final_context.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"Pipeline execution failed: {str(e)}")

if __name__ == "__main__":
    main()