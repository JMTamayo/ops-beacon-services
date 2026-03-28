import pytest
from pydantic import ValidationError

from fred_ops.config import ConfigError, FredOpsConfig, load_config


VALID_PUBSUB_YAML = """
broker:
  host: localhost
  port: 1883

mode: pubsub

input:
  topic: sensors/raw
  schema:
    device_id: str
    temperature: float
    active: bool

output:
  topic: sensors/out
  schema:
    device_id: str
    alert: bool
"""

VALID_PUB_YAML = """
broker:
  host: localhost
  port: 1883

mode: pub

output:
  topic: sensors/out
  schema:
    value: float
"""

VALID_SUB_YAML = """
broker:
  host: localhost
  port: 1883

mode: sub

input:
  topic: sensors/raw
  schema:
    device_id: str
    value: int
"""

YAML_WITH_KWARGS = """
broker:
  host: localhost
  port: 1883

mode: sub

input:
  topic: sensors/raw
  schema:
    value: int

kwargs:
  threshold: 42.5
  region: us-east
"""


def write_yaml(tmp_path, content: str):
    p = tmp_path / "config.yml"
    p.write_text(content)
    return str(p)


def test_load_valid_pubsub(tmp_path):
    path = write_yaml(tmp_path, VALID_PUBSUB_YAML)
    config, InputModel, OutputModel = load_config(path)
    assert config.mode == "pubsub"
    assert config.broker.host == "localhost"
    assert config.broker.port == 1883
    assert InputModel is not None
    assert OutputModel is not None


def test_load_valid_pub(tmp_path):
    path = write_yaml(tmp_path, VALID_PUB_YAML)
    config, InputModel, OutputModel = load_config(path)
    assert config.mode == "pub"
    assert InputModel is None
    assert OutputModel is not None


def test_load_valid_sub(tmp_path):
    path = write_yaml(tmp_path, VALID_SUB_YAML)
    config, InputModel, OutputModel = load_config(path)
    assert config.mode == "sub"
    assert InputModel is not None
    assert OutputModel is None


def test_pubsub_requires_input(tmp_path):
    yaml = """
broker:
  host: localhost
  port: 1883
mode: pubsub
output:
  topic: out
  schema:
    value: str
"""
    path = write_yaml(tmp_path, yaml)
    with pytest.raises(ConfigError, match="pubsub.*input"):
        load_config(path)


def test_pubsub_requires_output(tmp_path):
    yaml = """
broker:
  host: localhost
  port: 1883
mode: pubsub
input:
  topic: in
  schema:
    value: str
"""
    path = write_yaml(tmp_path, yaml)
    with pytest.raises(ConfigError, match="pubsub.*output"):
        load_config(path)


def test_pub_requires_output(tmp_path):
    yaml = """
broker:
  host: localhost
  port: 1883
mode: pub
input:
  topic: in
  schema:
    value: str
"""
    path = write_yaml(tmp_path, yaml)
    with pytest.raises(ConfigError, match="pub.*output"):
        load_config(path)


def test_sub_requires_input(tmp_path):
    yaml = """
broker:
  host: localhost
  port: 1883
mode: sub
output:
  topic: out
  schema:
    value: str
"""
    path = write_yaml(tmp_path, yaml)
    with pytest.raises(ConfigError, match="sub.*input"):
        load_config(path)


def test_invalid_mode(tmp_path):
    yaml = """
broker:
  host: localhost
  port: 1883
mode: invalid
"""
    path = write_yaml(tmp_path, yaml)
    with pytest.raises(ConfigError):
        load_config(path)


def test_schema_type_mapping(tmp_path):
    path = write_yaml(tmp_path, VALID_PUBSUB_YAML)
    _, InputModel, _ = load_config(path)
    fields = InputModel.model_fields
    assert fields["device_id"].annotation is str
    assert fields["temperature"].annotation is float
    assert fields["active"].annotation is bool


def test_input_model_instantiation(tmp_path):
    path = write_yaml(tmp_path, VALID_PUBSUB_YAML)
    _, InputModel, _ = load_config(path)
    obj = InputModel(device_id="abc", temperature=22.5, active=True)
    assert obj.device_id == "abc"
    assert obj.temperature == 22.5


def test_output_model_instantiation(tmp_path):
    path = write_yaml(tmp_path, VALID_PUBSUB_YAML)
    _, _, OutputModel = load_config(path)
    obj = OutputModel(device_id="abc", alert=False)
    assert obj.device_id == "abc"


def test_kwargs_from_yaml(tmp_path):
    path = write_yaml(tmp_path, YAML_WITH_KWARGS)
    config, _, _ = load_config(path)
    assert config.kwargs["threshold"] == 42.5
    assert config.kwargs["region"] == "us-east"


def test_kwargs_cli_override(tmp_path):
    path = write_yaml(tmp_path, YAML_WITH_KWARGS)
    config, _, _ = load_config(path, cli_kwargs={"region": "eu-west"})
    assert config.kwargs["region"] == "eu-west"
    assert config.kwargs["threshold"] == 42.5


def test_kwargs_empty_when_not_defined(tmp_path):
    path = write_yaml(tmp_path, VALID_PUBSUB_YAML)
    config, _, _ = load_config(path)
    assert config.kwargs == {}
