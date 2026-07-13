"""Tests for template directory discovery."""

import pytest

from forge.exceptions import AmbiguousTemplateDirError, TemplateDirNotFoundError
from forge.find import find_template


def test_finds_templated_dir(tmp_path):
    (tmp_path / "{{forge.project_id}}").mkdir()
    (tmp_path / "hooks").mkdir()
    (tmp_path / "README.md").write_text("docs")

    result = find_template(tmp_path)

    assert result == tmp_path / "{{forge.project_id}}"


def test_any_context_key_in_dir_name_is_accepted(tmp_path):
    (tmp_path / "{{cookiecutter.project_id}}").mkdir()

    result = find_template(tmp_path)

    assert result == tmp_path / "{{cookiecutter.project_id}}"


def test_no_templated_dir_raises(tmp_path):
    (tmp_path / "hooks").mkdir()

    with pytest.raises(TemplateDirNotFoundError):
        find_template(tmp_path)


def test_multiple_templated_dirs_raises(tmp_path):
    (tmp_path / "{{forge.a}}").mkdir()
    (tmp_path / "{{forge.b}}").mkdir()

    with pytest.raises(AmbiguousTemplateDirError):
        find_template(tmp_path)


def test_templated_file_is_ignored(tmp_path):
    (tmp_path / "{{forge.project_id}}").mkdir()
    (tmp_path / "{{forge.name}}.txt").write_text("not a dir")

    result = find_template(tmp_path)

    assert result == tmp_path / "{{forge.project_id}}"
