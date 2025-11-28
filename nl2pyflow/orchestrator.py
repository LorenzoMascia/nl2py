# core/orchestrator.py
import importlib.util
import sys
import os
from typing import List, Dict, Any

class Orchestrator:
    """
    Orchestrator that dynamically loads generated Python functions and executes them in sequence,
    passing a shared context dictionary between them.
    """
    
    def __init__(self, blocks_dir: str = "blocks"):
        """
        Initialize the Orchestrator.
        
        Args:
            blocks_dir (str): Directory containing generated block Python files.
        """
        self.blocks_dir = blocks_dir
    
    def run_pipeline(self, block_names: List[str]) -> Dict[str, Any]:
        """
        Executes the entire pipeline by running the blocks in sequence.
        
        Args:
            block_names (List[str]): List of block names to execute, in order.
            
        Returns:
            Dict[str, Any]: The final context dictionary after pipeline execution.
        """
        # Initialize empty context
        context = {}
        
        print(f"Starting pipeline execution with {len(block_names)} blocks")
        
        # Execute each block in sequence
        for block_name in block_names:
            try:
                print(f"Loading and executing {block_name}...")
                
                # Dynamically load the module
                module = self._load_module(block_name)
                
                # Get the function from the module
                block_function = getattr(module, block_name)
                
                # Execute the function with the current context
                context = block_function(context)
                
                # Validate that the function returned a dictionary
                if not isinstance(context, dict):
                    raise TypeError(f"Block {block_name} did not return a dictionary")
                    
                print(f"✓ {block_name} executed successfully")
                
            except Exception as e:
                print(f"❌ Error executing {block_name}: {str(e)}")
                raise
        
        print("Pipeline execution completed successfully")
        return context
    
    def _load_module(self, block_name: str):
        """
        Dynamically loads a Python module from a file.
        
        Args:
            block_name (str): Name of the block to load.
            
        Returns:
            module: The loaded Python module.
            
        Raises:
            FileNotFoundError: If the module file doesn't exist.
        """
        file_path = os.path.join(self.blocks_dir, f"{block_name}.py")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Block file not found: {file_path}")
        
        # Create a unique module name to avoid conflicts
        module_name = f"nl2pyflow_dynamic_{block_name}"
        
        # Load the module from file
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        return module