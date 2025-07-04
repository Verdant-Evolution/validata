from pathlib import Path
from typing import Callable, Literal, Sequence, cast
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, Static, TextArea
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual import events
from pydantic_ui.lib import import_model, load_data
from pydantic import BaseModel, ValidationError
import os
import yaml
import json

ParseFormat = Literal["json", "yaml"]
Parser = Callable[[str], dict]

PARSER_MAP = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}

PARSERS: dict[str, Parser] = {
    "json": json.loads,
    "yaml": yaml.safe_load,
}


class ValidationErrorPanel(Static):
    def update_errors(self, errors: str = ""):
        self.update(errors)


class FileEditorApp(App):
    CSS_PATH = None
    BINDINGS = [
        ("ctrl+s", "save", "Save"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+v", "validate", "Validate"),
    ]

    def __init__(
        self,
        model_class: type[BaseModel],
        file_path: Path | str,
        force_format: ParseFormat | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_class = model_class
        self.file_path = Path(file_path)

        parser = PARSERS.get(force_format or self.file_path.suffix.lstrip("."), None)
        if parser is None:
            raise ValueError("Unsupported file format")
        self.parser = parser

        self.validation_panel = ValidationErrorPanel()
        self.text_area = TextArea()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield self.text_area
            yield self.validation_panel
        yield Footer()

    def on_mount(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.text_area.text = f.read()
        else:
            self.text_area.text = ""
        self.action_validate()  # Validate immediately on load

    def action_save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(self.text_area.text)
        self.validation_panel.update_errors("File saved.")
        self.action_validate()  # Update validation panel after save
        self.notify("File saved.", timeout=2)

    def format_validation_errors(self, ve: ValidationError) -> str:
        lines = []
        model_fields = getattr(self.model_class, "__fields__", {})
        for err in ve.errors():
            loc: Sequence[int | str] = err.get("loc", [])
            loc_str = ".".join(str(x) for x in loc)
            msg = err.get("msg", "")
            typ = err.get("type", "")
            # If missing and required, show expected type
            if typ == "missing" and loc:
                field = model_fields.get(loc[0])
                if field is not None:
                    expected_type = field.annotation
                    msg += f" (expected type: {expected_type.__name__ if hasattr(expected_type, '__name__') else expected_type})"
            lines.append(f"- {loc_str}: {msg} [{typ}]")
        return "\n".join(lines)

    def action_validate(self):
        text = self.text_area.text
        try:
            try:
                data = self.parser(text)
            except json.JSONDecodeError as e:
                self.validation_panel.update_errors(
                    f"JSON parsing error at line {e.lineno}, column {e.colno}: {e.msg}"
                )
                return
            except yaml.YAMLError as e:
                self.validation_panel.update_errors(f"YAML parsing error: {str(e)}")
                return
            self.model_class(**data)
            self.validation_panel.update_errors("Validation successful!")
        except ValidationError as ve:
            self.validation_panel.update_errors(self.format_validation_errors(ve))
        except Exception as e:
            self.validation_panel.update_errors(f"Error: {e}")

    async def on_key(self, event: events.Key):
        if event.key == "f5":
            self.action_validate()
