from pathlib import Path
import json5


def load_config(filename):
    """Loads configuration from JSON5 file with basic error handling"""
    config_file = Path(__file__).parent / filename

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json5.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Configuration file not found: {config_file}") from e
    except Exception as e:
        raise ValueError(f"Error loading configuration: {e}") from e


def build_path(path_config):
    """Creates a path based on JSON configuration"""
    if path_config["type"] == "relative":
        base_path = Path(__file__).parents[path_config["up"]]
        return base_path / path_config["path"]
    elif path_config["type"] == "absolute":
        return Path(path_config["path"])
    else:
        raise ValueError(f"Unknown path type: {path_config['type']}")
