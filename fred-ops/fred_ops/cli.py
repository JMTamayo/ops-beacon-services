from __future__ import annotations

import asyncio
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import click

from fred_ops.app import FredOps
from fred_ops.config import ConfigError, load_config
from fred_ops.dashboard.recorder import init_dashboard_recorder
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


def _spawn_streamlit_dashboard(config_path: str, port: int, host: str) -> subprocess.Popen:
    try:
        import streamlit  # noqa: F401
    except ImportError as e:
        raise click.ClickException(
            "Dashboard is enabled but optional dependencies are missing. "
            "Install with: pip install 'fred-ops[dashboard]' (or uv sync --extra dashboard)."
        ) from e
    from fred_ops.dashboard import app as dash_app

    app_file = Path(dash_app.__file__).resolve()
    env = os.environ.copy()
    env["FRED_OPS_CONFIG_PATH"] = str(Path(config_path).resolve())
    args = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.port",
        str(port),
        "--server.address",
        host,
        "--browser.gatherUsageStats",
        "false",
    ]
    return subprocess.Popen(args, env=env)


def _terminate_process(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=12)
    except subprocess.TimeoutExpired:
        proc.kill()


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
        storage_fn = app.get_storage()
    except RuntimeError as e:
        raise click.ClickException(str(e))

    init_dashboard_recorder(fred_config)
    dash_proc: subprocess.Popen | None = None
    if fred_config.dashboard is not None and fred_config.dashboard.enabled:
        os.environ["FRED_OPS_CONFIG_PATH"] = str(Path(config).resolve())
        dash_proc = _spawn_streamlit_dashboard(
            config,
            fred_config.dashboard.port,
            fred_config.dashboard.host,
        )

    mode = fred_config.mode
    try:
        try:
            if mode == "pubsub":
                asyncio.run(
                    run_pubsub(fred_config, execute_fn, InputModel, OutputModel, storage_fn)
                )
            elif mode == "pub":
                asyncio.run(run_pub(fred_config, execute_fn, OutputModel, storage_fn))
            elif mode == "sub":
                asyncio.run(run_sub(fred_config, execute_fn, InputModel, storage_fn))
        except KeyboardInterrupt:
            click.echo("Stopped.")
    finally:
        _terminate_process(dash_proc)
