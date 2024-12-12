# conftest.py
import os

import pytest


@pytest.fixture(autouse=True)
def env_setup():    
    # Set environment variable
    os.environ["CONFIG_FILE_PATH"] = os.path.join(os.path.dirname(__file__), "config/models.yaml")
    
    yield
    
    # Clean up
    if "CONFIG_FILE_PATH" in os.environ:
        del os.environ["CONFIG_FILE_PATH"]
