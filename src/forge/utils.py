"""Helper functions used throughout Forge."""

import contextlib
import logging
import os
import shutil
import stat
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _force_delete(func, path, exc_info):
    """Error handler for ``shutil.rmtree()`` equivalent to ``rm -rf``."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rmtree(path):
    """Remove a directory and all its contents, like ``rm -rf``."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_force_delete)
    else:
        shutil.rmtree(path, onerror=_force_delete)


def make_sure_path_exists(path):
    """Ensure that a directory exists, creating the tree if needed."""
    logger.debug("Making sure path exists (creates tree if not exist): %s", path)
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise OSError(f"Unable to create directory at {path}") from error


@contextlib.contextmanager
def work_in(dirname=None):
    """Context manager version of ``os.chdir``.

    When exited, returns to the working directory prior to entering.
    """
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)


def make_executable(script_path):
    """Set the executable bit on ``script_path``."""
    status = os.stat(script_path)
    os.chmod(script_path, status.st_mode | stat.S_IEXEC)
