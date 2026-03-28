import sys
import textwrap

import pytest
from fred_ops.app import FredOps
from fred_ops.cli import _discover_fred_ops_instance


def test_execute_decorator_stores_function():
    app = FredOps()

    @app.execute
    async def my_execute(input, output, **kwargs):
        pass

    assert app.get_execute() is my_execute


def test_get_execute_raises_when_not_registered():
    app = FredOps()
    with pytest.raises(RuntimeError, match="No execute function registered"):
        app.get_execute()


def test_decorator_returns_original_function():
    app = FredOps()

    @app.execute
    async def my_fn():
        pass

    assert my_fn.__name__ == "my_fn"


def test_registering_twice_raises():
    app = FredOps()

    @app.execute
    async def fn1():
        pass

    with pytest.raises(RuntimeError, match="already registered"):
        @app.execute
        async def fn2():
            pass


def test_discover_fred_ops_instance_from_script(tmp_path):
    script = tmp_path / "processor.py"
    script.write_text(textwrap.dedent("""
        from fred_ops import FredOps
        app = FredOps()

        @app.execute
        async def execute(input, output, **kwargs):
            pass
    """))
    app = _discover_fred_ops_instance(str(script))
    from fred_ops.app import FredOps as FredOpsClass
    assert isinstance(app, FredOpsClass)


def test_discover_raises_when_no_instance(tmp_path):
    script = tmp_path / "empty.py"
    script.write_text("x = 1\n")
    with pytest.raises(RuntimeError, match="No FredOps instance"):
        _discover_fred_ops_instance(str(script))
