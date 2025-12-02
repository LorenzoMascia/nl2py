"""
AIBasic Compiler - Test Package
This package contains all unit and integration tests.
"""

import sys
import pathlib

# Ensure that the project "src" directory is on sys.path
# so that tests can import aibasic.* modules directly.
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Optional: enable simple test-time logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)

# You can also define global test fixtures here if needed later
# For example:
# import pytest
#
# @pytest.fixture(scope="session")
# def sample_context():
#     return {"description": "test context"}
