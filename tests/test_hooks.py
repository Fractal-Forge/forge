"""Tests for pre/post generation hooks."""

import pytest

from forge import generate
from forge.exceptions import FailedHookError

CONTEXT = {"project_id": "demo", "marker": "from-context"}


def make_repo(tmp_path):
    repo = tmp_path / "template"
    (repo / "{{forge.project_id}}").mkdir(parents=True)
    (repo / "{{forge.project_id}}" / "file.txt").write_text("x", encoding="utf-8")
    (repo / "hooks").mkdir()
    return repo


def test_post_gen_hook_runs_in_project_dir_and_is_rendered(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "hooks" / "post_gen_project.py").write_text(
        "from pathlib import Path\n"
        "Path('hook_output.txt').write_text('{{ forge.marker }}')\n",
        encoding="utf-8",
    )

    project_dir = generate(repo, CONTEXT, tmp_path / "out")

    assert (project_dir / "hook_output.txt").read_text() == "from-context"


def test_pre_gen_hook_runs(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "hooks" / "pre_gen_project.py").write_text(
        "from pathlib import Path\nPath('pre_marker.txt').write_text('pre')\n",
        encoding="utf-8",
    )

    project_dir = generate(repo, CONTEXT, tmp_path / "out")

    assert (project_dir / "pre_marker.txt").exists()
    assert (project_dir / "file.txt").exists()


def test_failing_hook_raises_and_cleans_up(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "hooks" / "post_gen_project.py").write_text(
        "import sys\nsys.exit(1)\n", encoding="utf-8"
    )
    out = tmp_path / "out"

    with pytest.raises(FailedHookError):
        generate(repo, CONTEXT, out)

    assert not (out / "demo").exists()


def test_failing_hook_keeps_project_when_asked(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "hooks" / "post_gen_project.py").write_text(
        "import sys\nsys.exit(1)\n", encoding="utf-8"
    )
    out = tmp_path / "out"

    with pytest.raises(FailedHookError):
        generate(repo, CONTEXT, out, keep_project_on_failure=True)

    assert (out / "demo" / "file.txt").exists()


def test_accept_hooks_false_skips_hooks(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "hooks" / "post_gen_project.py").write_text(
        "import sys\nsys.exit(1)\n", encoding="utf-8"
    )

    project_dir = generate(repo, CONTEXT, tmp_path / "out", accept_hooks=False)

    assert (project_dir / "file.txt").exists()


def test_backup_hook_files_are_ignored(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "hooks" / "post_gen_project.py~").write_text(
        "import sys\nsys.exit(1)\n", encoding="utf-8"
    )

    project_dir = generate(repo, CONTEXT, tmp_path / "out")

    assert (project_dir / "file.txt").exists()
