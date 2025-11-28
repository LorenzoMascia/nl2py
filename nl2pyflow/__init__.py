"""
NL2PyFlow - Natural Language to Python Flow

A pipeline that converts high level natural language blocks into executable
Python functions, chained together with a shared context.
"""

__version__ = "0.1.0"
__author__ = "Lorenzo Mascia"
__email__ = "lorenzo.mascia@gmail.com"

from nl2pyflow.block_parser import parse_blocks
from nl2pyflow.code_generator import generate_code_for_block
from nl2pyflow.orchestrator import Orchestrator

__all__ = [
    "parse_blocks",
    "generate_code_for_block",
    "Orchestrator",
]
