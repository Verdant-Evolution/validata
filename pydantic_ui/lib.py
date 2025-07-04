import importlib
import importlib.util
import sys
from pathlib import Path
from pydantic import BaseModel
import yaml
import json

def import_model(model_path: str):
    """
    Import a Pydantic model class from a given path.
    Supports:
      - <location/to/file.py>:<model_class>
      - <location.to.module>:<model_class>
    """
    if ":" not in model_path:
        raise ValueError(
            "Model path must be in the format <module_or_file>:<model_class>"
        )
    location, class_name = model_path.rsplit(":", 1)

    if not class_name.isidentifier():
        raise ValueError(
            f"Invalid class name '{class_name}'. Must be a valid Python identifier."
        )

    if location.endswith(".py"):
        path = Path(location)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path.absolute()}")
    else:
        if not all(part.isidentifier() for part in location.split(".")):
            raise ValueError(
                f"Invalid module path '{location}'. Must be a valid Python module path."
            )

    if location.endswith(".py"):
        spec = importlib.util.spec_from_file_location("user_module", location)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {location}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["user_module"] = module
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(location)

    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise ImportError(f"Model class '{class_name}' not found in '{location}'")

    if not isinstance(model_class, type) or not issubclass(model_class, BaseModel):
        raise TypeError(
            f"{getattr(model_class, '__name__', str(model_class))} is not a subclass of pydantic.BaseModel."
        )
    return model_class


def load_data(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith(".yaml") or file_path.endswith(".yml"):
            return yaml.safe_load(f)
        elif file_path.endswith(".json"):
            return json.load(f)
        else:
            raise ValueError("Input file must be .yaml, .yml, or .json")
