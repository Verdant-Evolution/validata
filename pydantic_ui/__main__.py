from pathlib import Path
import sys
from .editor import FileEditorApp
from .lib import import_model


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Edit and validate YAML/JSON files against a Pydantic model."
    )
    parser.add_argument(
        "model",
        help="Model location: <file.py>:<Model> or <module.path>:<Model>",
    )
    parser.add_argument("file", help="Input YAML or JSON file to edit/validate")
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        help="Force file format for parsing (json or yaml)",
    )
    args = parser.parse_args()
    try:
        model_class = import_model(args.model)
    except Exception as e:
        print(f"Error importing model: {e}", file=sys.stderr)
        sys.exit(1)
    FileEditorApp(model_class, args.file, force_format=args.format).run()


if __name__ == "__main__":
    main()
