"""Discovery and execution of pre/post generation hooks.

Hook scripts live in a ``hooks/`` directory next to the templated project
directory. They are rendered through Jinja with the same context as the
template files, then executed with the generated project directory as the
working directory.
"""

import errno
import logging
import os
import subprocess  # nosec
import sys
import tempfile

from forge.exceptions import FailedHookError
from forge.utils import make_executable

logger = logging.getLogger(__name__)

_HOOKS = [
    "pre_gen_project",
    "post_gen_project",
]
EXIT_SUCCESS = 0


def find_hook(hook_name, hooks_dir):
    """Return the hook scripts for ``hook_name``, sorted for determinism.

    :param hook_name: The hook to find, e.g. ``post_gen_project``.
    :param hooks_dir: The ``hooks/`` directory of the template repo.
    :return: List of absolute paths to matching hook scripts (may be empty).
    """
    if hook_name not in _HOOKS:
        raise ValueError(f"Unknown hook name: {hook_name}")

    if not os.path.isdir(hooks_dir):
        logger.debug("No hooks/ dir in template repo")
        return []

    scripts = []
    for hook_file in sorted(os.listdir(hooks_dir)):
        basename = os.path.splitext(os.path.basename(hook_file))[0]
        if basename == hook_name and not hook_file.endswith("~"):
            scripts.append(os.path.abspath(os.path.join(hooks_dir, hook_file)))
    return scripts


def run_script(script_path, cwd="."):
    """Execute a script from a working directory.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    """
    run_thru_shell = sys.platform.startswith("win")
    if script_path.endswith(".py"):
        script_command = [sys.executable, script_path]
    else:
        script_command = [script_path]

    make_executable(script_path)

    try:
        proc = subprocess.Popen(  # nosec
            script_command, shell=run_thru_shell, cwd=cwd
        )
        exit_status = proc.wait()
        if exit_status != EXIT_SUCCESS:
            raise FailedHookError(f"Hook script failed (exit status: {exit_status})")
    except OSError as err:
        if err.errno == errno.ENOEXEC:
            raise FailedHookError(
                "Hook script failed, might be an empty file or missing a shebang"
            ) from err
        raise FailedHookError(f"Hook script failed (error: {err})") from err


def run_script_with_context(script_path, cwd, jinja_context, env):
    """Render a script with Jinja and execute it.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    :param jinja_context: The full Jinja context, ``{context_key: {...}}``.
    :param env: The Jinja environment used for template rendering.
    """
    _, extension = os.path.splitext(script_path)

    with open(script_path, encoding="utf-8") as file:
        contents = file.read()

    with tempfile.NamedTemporaryFile(delete=False, mode="wb", suffix=extension) as temp:
        output = env.from_string(contents).render(**jinja_context)
        temp.write(output.encode("utf-8"))

    try:
        run_script(temp.name, cwd)
    finally:
        os.remove(temp.name)


def run_hook(hook_name, hooks_dir, project_dir, jinja_context, env):
    """Find and execute all scripts for a hook, if any.

    :param hook_name: The hook to execute.
    :param hooks_dir: The ``hooks/`` directory of the template repo.
    :param project_dir: The directory to execute the scripts from.
    :param jinja_context: The full Jinja context, ``{context_key: {...}}``.
    :param env: The Jinja environment used for template rendering.
    """
    scripts = find_hook(hook_name, hooks_dir)
    if not scripts:
        logger.debug("No %s hook found", hook_name)
        return
    logger.debug("Running hook %s", hook_name)
    for script in scripts:
        run_script_with_context(script, project_dir, jinja_context, env)
