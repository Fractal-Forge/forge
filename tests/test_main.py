"""End-to-end tests for the rendering engine."""

import os
import stat

import pytest
from jinja2.ext import Extension

from forge import forge
from forge.exceptions import (
    OutputDirExistsError,
    UndefinedVariableInTemplateError,
    UnknownExtensionError,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x01"


def make_repo(tmp_path, key="forge"):
    """Create a minimal template repo and return its path."""
    repo = tmp_path / "template"
    tdir = repo / ("{{%s.project_id}}" % key)
    pkg = tdir / ("src/{{%s.name_snake}}" % key)
    pkg.mkdir(parents=True)
    (tdir / "README.md.jinja2").write_text("# {{ %s.name }}\n" % key, encoding="utf-8")
    (pkg / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (tdir / "logo.png").write_bytes(PNG_BYTES)
    return repo


CONTEXT = {"project_id": "demo", "name": "Demo", "name_snake": "demo_app"}


def test_renders_project_tree(tmp_path):
    repo = make_repo(tmp_path)
    out = tmp_path / "out"

    project_dir = forge(repo, CONTEXT, out, context_key="forge")

    assert project_dir == out / "demo"
    assert (project_dir / "README.md").read_text() == "# Demo\n"
    assert (project_dir / "src/demo_app/__init__.py").exists()


def test_context_key_defaults_to_forge(tmp_path):
    repo = make_repo(tmp_path)

    project_dir = forge(repo, CONTEXT, tmp_path / "out")

    assert project_dir.name == "demo"


def test_custom_context_key(tmp_path):
    repo = make_repo(tmp_path, key="cookiecutter")
    out = tmp_path / "out"

    project_dir = forge(repo, CONTEXT, out, context_key="cookiecutter")

    assert (project_dir / "README.md").read_text() == "# Demo\n"


def test_remove_file_extension_defaults_to_jinja2(tmp_path):
    repo = make_repo(tmp_path)

    project_dir = forge(repo, CONTEXT, tmp_path / "out")

    assert (project_dir / "README.md").exists()
    assert not (project_dir / "README.md.jinja2").exists()


def test_remove_file_extension_only_strips_suffix(tmp_path):
    repo = make_repo(tmp_path)
    tdir = repo / "{{forge.project_id}}"
    (tdir / "config.jinja2.md").write_text("keep name", encoding="utf-8")

    project_dir = forge(repo, CONTEXT, tmp_path / "out")

    assert (project_dir / "README.md").exists()
    assert (project_dir / "config.jinja2.md").exists()


def test_remove_file_extension_accepts_a_tuple(tmp_path):
    repo = make_repo(tmp_path)
    tdir = repo / "{{forge.project_id}}"
    (tdir / "short.j2").write_text("short form", encoding="utf-8")

    project_dir = forge(
        repo, CONTEXT, tmp_path / "out", remove_file_extension=(".jinja2", ".j2")
    )

    assert (project_dir / "README.md").exists()
    assert (project_dir / "short").exists()


def test_remove_file_extension_none_disables_stripping(tmp_path):
    repo = make_repo(tmp_path)

    project_dir = forge(repo, CONTEXT, tmp_path / "out", remove_file_extension=None)

    assert (project_dir / "README.md.jinja2").exists()


def test_binary_copied_verbatim(tmp_path):
    repo = make_repo(tmp_path)

    project_dir = forge(repo, CONTEXT, tmp_path / "out")

    assert (project_dir / "logo.png").read_bytes() == PNG_BYTES


def test_undefined_variable_raises_and_cleans_up(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "{{forge.project_id}}" / "bad.txt").write_text(
        "{{ forge.missing }}", encoding="utf-8"
    )
    out = tmp_path / "out"

    with pytest.raises(UndefinedVariableInTemplateError) as excinfo:
        forge(repo, CONTEXT, out)

    assert "bad.txt" in str(excinfo.value)
    assert not (out / "demo").exists()


def test_undefined_variable_keeps_preexisting_output_dir(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "{{forge.project_id}}" / "bad.txt").write_text(
        "{{ forge.missing }}", encoding="utf-8"
    )
    out = tmp_path / "out"
    (out / "demo").mkdir(parents=True)

    with pytest.raises(UndefinedVariableInTemplateError):
        forge(repo, CONTEXT, out, overwrite_if_exists=True)

    assert (out / "demo").exists()


def test_output_dir_exists_raises_without_overwrite(tmp_path):
    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    (out / "demo").mkdir(parents=True)

    with pytest.raises(OutputDirExistsError):
        forge(repo, CONTEXT, out)


def test_overwrite_if_exists_rerenders(tmp_path):
    repo = make_repo(tmp_path)
    out = tmp_path / "out"

    forge(repo, CONTEXT, out)
    project_dir = forge(repo, CONTEXT, out, overwrite_if_exists=True)

    assert (project_dir / "README.md").read_text() == "# Demo\n"


def test_skip_if_file_exists_preserves_content(tmp_path):
    repo = make_repo(tmp_path)
    out = tmp_path / "out"
    project_dir = forge(repo, CONTEXT, out)
    (project_dir / "README.md").write_text("hand-edited", encoding="utf-8")

    forge(
        repo,
        CONTEXT,
        out,
        overwrite_if_exists=True,
        skip_if_file_exists=True,
    )

    assert (project_dir / "README.md").read_text() == "hand-edited"


def test_copy_without_render_keeps_jinja_syntax(tmp_path):
    repo = make_repo(tmp_path)
    raw_dir = repo / "{{forge.project_id}}" / "raw"
    raw_dir.mkdir()
    (raw_dir / "template.txt").write_text("{{ not_rendered }}", encoding="utf-8")

    project_dir = forge(repo, CONTEXT, tmp_path / "out", copy_without_render=["raw"])

    assert (project_dir / "raw/template.txt").read_text() == "{{ not_rendered }}"


def test_empty_conditional_filename_is_skipped(tmp_path):
    repo = make_repo(tmp_path)
    tdir = repo / "{{forge.project_id}}"
    (tdir / "{% if forge.flag %}extra.txt{% endif %}").write_text(
        "conditional", encoding="utf-8"
    )

    project_dir = forge(repo, {**CONTEXT, "flag": False}, tmp_path / "out")

    assert not (project_dir / "extra.txt").exists()
    project_dir_2 = forge(repo, {**CONTEXT, "flag": True}, tmp_path / "out2")
    assert (project_dir_2 / "extra.txt").read_text() == "conditional"


def test_exec_bit_preserved(tmp_path):
    repo = make_repo(tmp_path)
    script = repo / "{{forge.project_id}}" / "run.sh"
    script.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    script.chmod(0o755)

    project_dir = forge(repo, CONTEXT, tmp_path / "out")

    mode = os.stat(project_dir / "run.sh").st_mode
    assert mode & stat.S_IXUSR


def test_trailing_newline_preserved(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "{{forge.project_id}}" / "exact.txt").write_text("line\n", encoding="utf-8")

    project_dir = forge(repo, CONTEXT, tmp_path / "out")

    assert (project_dir / "exact.txt").read_bytes() == b"line\n"


def test_newline_override(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "{{forge.project_id}}" / "crlf.txt").write_text("a\nb\n", encoding="utf-8")

    project_dir = forge(repo, CONTEXT, tmp_path / "out", newline="\r\n")

    assert (project_dir / "crlf.txt").read_bytes() == b"a\r\nb\r\n"


class UpperExtension(Extension):
    """Test extension mirroring the studio's StringOperationsExtension."""

    def __init__(self, environment):
        super().__init__(environment)
        environment.filters["shout"] = lambda value: value.upper()


def test_extension_class_filter(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "{{forge.project_id}}" / "shout.txt").write_text(
        "{{ forge.name|shout }}", encoding="utf-8"
    )

    project_dir = forge(repo, CONTEXT, tmp_path / "out", extensions=[UpperExtension])

    assert (project_dir / "shout.txt").read_text() == "DEMO"


def test_extension_import_path_string(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "{{forge.project_id}}" / "do.txt").write_text(
        "{% set items = [] %}{% do items.append(forge.name) %}{{ items[0] }}",
        encoding="utf-8",
    )

    project_dir = forge(repo, CONTEXT, tmp_path / "out", extensions=["jinja2.ext.do"])

    assert (project_dir / "do.txt").read_text() == "Demo"


def test_unknown_extension_raises(tmp_path):
    repo = make_repo(tmp_path)

    with pytest.raises(UnknownExtensionError):
        forge(repo, CONTEXT, tmp_path / "out", extensions=["no.such.Extension"])
