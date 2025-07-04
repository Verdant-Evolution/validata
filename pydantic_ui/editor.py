from pathlib import Path
from typing import Callable, Literal, Sequence
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, Static, TextArea
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual import events
from pydantic_ui.lib import get_initial_content, Parser as PydanticParser
from pydantic import BaseModel, ValidationError
import os
import yaml
import json

ParseFormat = Literal["json", "yaml"]

PARSER_MAP = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}


class Parser:
    def __init__(self, parse_func, unparse_func):
        self.parse_func = parse_func
        self.unparse_func = unparse_func

    def parse(self, text: str):
        return self.parse_func(text)

    def unparse(self, data) -> str:
        return self.unparse_func(data)


PARSERS: dict[str, Parser] = {
    "json": Parser(json.loads, lambda d: json.dumps(d, indent=2)),
    "yaml": Parser(yaml.safe_load, lambda d: yaml.safe_dump(d, sort_keys=False)),
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
        force_clean: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_class = model_class
        self.file_path = Path(file_path)
        self.force_clean = force_clean

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
        initial_content = ""
        if not self.force_clean:
            if self.file_path.exists():
                initial_content = self.file_path.read_text()
            else:
                try:
                    data = get_initial_content(self.model_class)
                    initial_content = self.parser.unparse(data)
                except Exception as e:
                    initial_content = ""
                    self.notify(
                        f"Default serialization failed for {self.model_class.__name__}",
                        severity="error",
                        timeout=4,
                    )

        self.text_area.text = initial_content
        self.action_validate()

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
                data = self.parser.parse(text)
            except json.JSONDecodeError as e:
                self.validation_panel.update_errors(
                    f"JSON parsing error at line {e.lineno}, column {e.colno}: {e.msg}"
                )
                return
            except yaml.YAMLError as e:
                self.validation_panel.update_errors(f"YAML parsing error: {str(e)}")
                return
            self.model_class(**data)
            self.validation_panel.update_errors("")
        except ValidationError as ve:
            self.validation_panel.update_errors(self.format_validation_errors(ve))
        except Exception as e:
            self.validation_panel.update_errors(f"Error: {e}")

    def action_save(self):
        self.file_path.write_text(self.text_area.text)
        self.action_validate()  # Update validation panel after save
        self.notify("File saved.", timeout=2)

    async def on_key(self, event: events.Key):
        if event.key == "f5":
            self.action_validate()
