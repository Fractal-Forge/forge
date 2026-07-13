"""Locate the templated project directory inside a template repo."""

import logging
import os
from pathlib import Path

from forge.exceptions import AmbiguousTemplateDirError, TemplateDirNotFoundError

logger = logging.getLogger(__name__)


def find_template(repo_dir):
    """Determine which child directory of ``repo_dir`` is the project template.

    The template directory is the one whose name contains Jinja2 syntax
    (``{{ ... }}``). Sibling entries such as ``hooks/``, ``fragments/`` or
    documentation are ignored.

    :param repo_dir: Directory containing the template.
    :return: Path to the templated project directory.
    """
    candidates = [
        entry
        for entry in sorted(os.listdir(repo_dir))
        if "{{" in entry
        and "}}" in entry
        and os.path.isdir(os.path.join(repo_dir, entry))
    ]

    if not candidates:
        raise TemplateDirNotFoundError(
            f"No templated ({{{{ ... }}}}) directory found in {repo_dir}"
        )
    if len(candidates) > 1:
        raise AmbiguousTemplateDirError(
            f"Multiple templated directories found in {repo_dir}: {candidates}"
        )

    project_template = Path(repo_dir, candidates[0])
    logger.debug("The project template appears to be %s", project_template)
    return project_template
