# Load config.json and returns a dictionary with the configuration.

# Path: util/load_config.py
import os
import json
from types import MappingProxyType

def load_config():
    """Load config.json and returns a dictionary with the configuration."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Return an immutable dictionary
    return MappingProxyType(config)
