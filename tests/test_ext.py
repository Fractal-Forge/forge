"""Behaviour lock for StringOperationsExtension.

The generator templates depend on the *exact* casing behaviour of these
filters (how ``snake`` splits existing CamelCase, how ``camel`` recombines,
etc.). These tests freeze that behaviour so a refactor can't silently change
generated output — this is the single source of truth both the studio and the
generator-templates render test rely on.
"""

import pytest
from jinja2 import Environment, StrictUndefined

from forge import StringOperationsExtension, forge

SNAKE = StringOperationsExtension.snake
CAMEL = StringOperationsExtension.camel
DASH = StringOperationsExtension.dash


@pytest.mark.parametrize(
    "value,expected",
    [
        ("MyEntity", "my_entity"),
        ("myEntity", "my_entity"),
        ("My Entity", "my_entity"),
        ("my-entity", "my_entity"),
        ("my_entity", "my_entity"),
        ("My  Entity", "my_entity"),  # collapse repeated separators
        ("--My__Entity--", "my_entity"),  # strip leading/trailing underscores
        ("HTTPServer", "http_server"),
        ("member_ids", "member_ids"),
    ],
)
def test_snake(value, expected):
    assert SNAKE(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("my_entity", "MyEntity"),
        ("my entity", "MyEntity"),
        ("myEntity", "MyEntity"),
        ("my-entity", "MyEntity"),
    ],
)
def test_camel(value, expected):
    assert CAMEL(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("MyEntity", "my-entity"),
        ("my_entity", "my-entity"),
        ("My Entity", "my-entity"),
    ],
)
def test_dash(value, expected):
    assert DASH(value) == expected


def test_lower_upper():
    assert StringOperationsExtension.lower("MiXeD") == "mixed"
    assert StringOperationsExtension.upper("MiXeD") == "MIXED"


def test_slug():
    # Requires the [filters] extra (python-slugify), installed in the dev group.
    assert StringOperationsExtension.slug("Héllo, World!") == "hello-world"


def test_filters_register_in_environment():
    env = Environment(undefined=StrictUndefined)
    StringOperationsExtension(env)
    assert env.from_string("{{ 'MyEntity'|snake }}").render() == "my_entity"
    assert env.from_string("{{ 'my_entity'|camel }}").render() == "MyEntity"
    assert env.from_string("{{ 'MyEntity'|dash }}").render() == "my-entity"


def test_extension_via_forge_render(tmp_path):
    """The extension resolves and applies when passed to forge()."""
    repo = tmp_path / "template"
    tdir = repo / "{{forge.project_id}}"
    tdir.mkdir(parents=True)
    (tdir / "out.txt").write_text("{{ forge.name|snake }}\n", encoding="utf-8")

    project_dir = forge(
        repo,
        {"project_id": "demo", "name": "MyCoolEntity"},
        tmp_path / "out",
        extensions=[StringOperationsExtension],
    )

    assert (project_dir / "out.txt").read_text() == "my_cool_entity\n"
