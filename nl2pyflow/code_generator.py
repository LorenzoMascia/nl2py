import os
import ast
from typing import Dict
from llm.llm_handler import OpenAIClient  
from dotenv import load_dotenv

PROMPT_TEMPLATE = """
You are a Python expert. Generate a function based on the following description:

Block name: {block_name}
Description: "{block_description}"

Requirements:
- Signature: def {block_name}(context: dict) -> dict
- Read and write using the `context` dictionary.
- Return python code only without any other description
"""

def generate_prompt(block: Dict[str, str]) -> str:
    """
    Creates a standardized LLM prompt from a block description.
    """
    return PROMPT_TEMPLATE.format(
        block_name=block["name"],
        block_description=block["description"]
    )

def is_valid_python(code: str) -> bool:
    """
    Checks if the generated Python code is syntactically correct.
    """
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        print(f"Syntax error: {e}")
        return False

def generate_code_for_block(block: Dict[str, str], output_dir="blocks") -> str:
    """
    Generates Python code for a block using an LLM, validates it, and saves to file.

    Args:
        block (Dict[str, str]): The parsed block.
        output_dir (str): Directory to save the generated Python files.
        llm (LLM): Optional LLM instance; if not passed, a new one is created.

    Returns:
        str: The file path of the generated code.
    """

    # Carica le variabili dal file .env
    load_dotenv()

    # Legge la variabile d'ambiente
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    llm_model = os.getenv("LLM_MODEL")

    if llm_model == None:
        llm_model = ""
    
    os.makedirs(output_dir, exist_ok=True)
    prompt = generate_prompt(block)

    # Use provided LLM or create a default one
    client = OpenAIClient(
        api_key=api_key,
        api_base=api_base,
        model=llm_model
    )
    
    code = client.get_python(prompt)

    if not is_valid_python(code):
        raise ValueError(f"Generated code {code} for {block['name']} is not valid Python.")

    file_path = os.path.join(output_dir, f"{block['name']}.py")
    with open(file_path, "w") as f:
        f.write(code)

    return file_path
