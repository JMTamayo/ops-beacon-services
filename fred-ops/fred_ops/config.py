from __future__ import annotations

import os
import yaml
from pydantic import BaseModel, create_model, model_validator
from typing import Any


TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}

VALID_MODES = {"pubsub", "pub", "sub"}


class ConfigError(Exception):
    pass


class BrokerConfig(BaseModel):
    host: str
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str | None = None


class TopicConfig(BaseModel):
    topic: str
    schema_: dict[str, str] = {}

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def remap_schema_key(cls, obj: Any) -> Any:
        if isinstance(obj, dict) and "schema" in obj:
            obj = dict(obj)
            obj["schema_"] = obj.pop("schema")
        return obj


class FredOpsConfig(BaseModel):
    broker: BrokerConfig
    mode: str
    input: TopicConfig | None = None
    output: TopicConfig | None = None
    kwargs: dict[str, Any] = {}

    @model_validator(mode="after")
    def validate_mode_sections(self) -> "FredOpsConfig":
        if self.mode not in VALID_MODES:
            raise ValueError(f"Invalid mode '{self.mode}'. Must be one of: {sorted(VALID_MODES)}")
        if self.mode == "pubsub":
            if self.input is None:
                raise ValueError("pubsub mode requires an input section")
            if self.output is None:
                raise ValueError("pubsub mode requires an output section")
        elif self.mode == "pub":
            if self.output is None:
                raise ValueError("pub mode requires an output section")
        elif self.mode == "sub":
            if self.input is None:
                raise ValueError("sub mode requires an input section")
        return self


def _build_model(name: str, schema: dict[str, str]) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for field_name, type_str in schema.items():
        if type_str not in TYPE_MAP:
            raise ConfigError(f"Unsupported type '{type_str}' for field '{field_name}'. Supported: {list(TYPE_MAP)}")
        fields[field_name] = (TYPE_MAP[type_str], ...)
    return create_model(name, **fields)


def load_config(
    path: str,
    cli_kwargs: dict[str, Any] | None = None,
) -> tuple[FredOpsConfig, type[BaseModel] | None, type[BaseModel] | None]:
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file is empty or not a valid YAML mapping: {path}")

    try:
        config = FredOpsConfig.model_validate(raw)
    except Exception as e:
        raise ConfigError(str(e)) from e

    # Merge kwargs: YAML values are base, CLI values override
    merged_kwargs = dict(config.kwargs)
    if cli_kwargs:
        merged_kwargs.update(cli_kwargs)
    config.kwargs = merged_kwargs

    InputModel = None
    OutputModel = None

    if config.input is not None:
        InputModel = _build_model("InputModel", config.input.schema_)

    if config.output is not None:
        OutputModel = _build_model("OutputModel", config.output.schema_)

    return config, InputModel, OutputModel
