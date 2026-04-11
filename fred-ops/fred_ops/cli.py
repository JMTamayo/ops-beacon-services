from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

import click

from fred_ops.app import FredOps
from fred_ops.config import ConfigError, load_config
from fred_ops.runtime.pubsub import run_pubsub
from fred_ops.runtime.pub import run_pub
from fred_ops.runtime.sub import run_sub


def _discover_fred_ops_instance(script_path: str) -> FredOps:
    path = Path(script_path).resolve()
    if not path.is_file():
        raise RuntimeError(f"Script file not found: '{script_path}'")
    module_key = f"_fred_ops_user_script_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_key, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_key] = module
    spec.loader.exec_module(module)

    for obj in vars(module).values():
        if isinstance(obj, FredOps):
            return obj

    raise RuntimeError(
        f"No FredOps instance found in '{script_path}'. "
        "Make sure you have `app = FredOps()` and `@app.execute` in your script."
    )


def _parse_kwarg(ctx, param, value) -> dict[str, str]:
    result = {}
    for item in value:
        if "=" not in item:
            raise click.BadParameter(f"Expected key=value format, got: '{item}'")
        k, v = item.split("=", 1)
        result[k.strip()] = v.strip()
    return result


@click.group()
def main() -> None:
    pass


@main.command()
@click.option("--config", "-c", required=True, help="Path to YAML config file")
@click.option("--script", "-s", required=True, help="Path to Python script with FredOps instance")
@click.option("--kwarg", "-k", multiple=True, callback=_parse_kwarg, is_eager=False, help="Extra key=value forwarded to execute (repeatable)")
def run(config: str, script: str, kwarg: dict[str, str]) -> None:
    """Launch an MQTT processor from a config file and script."""
    try:
        fred_config, InputModel, OutputModel = load_config(config, cli_kwargs=kwarg)
    except ConfigError as e:
        raise click.ClickException(str(e))

    try:
        app = _discover_fred_ops_instance(script)
        execute_fn = app.get_execute()
    except RuntimeError as e:
        raise click.ClickException(str(e))

    mode = fred_config.mode
    try:
        if mode == "pubsub":
            asyncio.run(run_pubsub(fred_config, execute_fn, InputModel, OutputModel))
        elif mode == "pub":
            asyncio.run(run_pub(fred_config, execute_fn, OutputModel))
        elif mode == "sub":
            asyncio.run(run_sub(fred_config, execute_fn, InputModel))
    except KeyboardInterrupt:
        click.echo("Stopped.")
