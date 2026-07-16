"""Render a project from a Fractal Forge template directory.

The core rendering walk is derived from Cookiecutter's ``generate.py``
(BSD-3-Clause) so that output stays byte-identical, with everything the
Fractal Forge generator never used removed. Configuration that Cookiecutter
read from a ``cookiecutter.json`` context file or underscore-prefixed context
keys is expressed as explicit parameters instead.
"""

import fnmatch
import logging
import os
import shutil
from pathlib import Path

from binaryornot.check import is_binary
from jinja2 import FileSystemLoader
from jinja2.exceptions import TemplateSyntaxError, UndefinedError

from forge.environment import create_environment
from forge.exceptions import (
    FailedHookError,
    OutputDirExistsError,
    UndefinedVariableInTemplateError,
)
from forge.find import find_template
from forge.hooks import run_hook
from forge.utils import make_sure_path_exists, rmtree, work_in

logger = logging.getLogger(__name__)


def _is_copy_only_path(path, copy_without_render):
    """Check whether ``path`` should only be copied and not rendered."""
    return any(fnmatch.fnmatch(path, pattern) for pattern in copy_without_render)


def _normalize_extensions(remove_file_extension):
    """Coerce a str/list/tuple/falsy extension spec into a tuple of suffixes."""
    if not remove_file_extension:
        return ()
    if isinstance(remove_file_extension, str):
        return (remove_file_extension,)
    return tuple(remove_file_extension)


def _render_and_create_dir(
    dirname, jinja_context, output_dir, env, overwrite_if_exists
):
    """Render the name of a directory, create it, and return its path."""
    rendered_dirname = env.from_string(dirname).render(**jinja_context)

    dir_to_create = Path(output_dir, rendered_dirname)

    logger.debug(
        "Rendered dir %s must exist in output_dir %s", dir_to_create, output_dir
    )

    output_dir_exists = dir_to_create.exists()

    if output_dir_exists:
        if overwrite_if_exists:
            logger.debug(
                "Output directory %s already exists, overwriting it", dir_to_create
            )
        else:
            raise OutputDirExistsError(
                f'Error: "{dir_to_create}" directory already exists'
            )
    else:
        make_sure_path_exists(dir_to_create)

    return dir_to_create, not output_dir_exists


def _generate_file(
    project_dir,
    infile,
    jinja_context,
    env,
    remove_file_extension,
    skip_if_file_exists,
    newline_override,
):
    """Render the filename and contents of ``infile`` into ``project_dir``.

    Binary files are copied over without rendering. Must be called with the
    template directory as the current working directory.
    """
    logger.debug("Processing file %s", infile)

    outfile_rendered = env.from_string(infile).render(**jinja_context)
    file_ext = os.path.splitext(outfile_rendered)[-1]
    if file_ext and file_ext in remove_file_extension:
        outfile_rendered = outfile_rendered[: -len(file_ext)]
    outfile = os.path.join(project_dir, outfile_rendered)

    # A conditional file name (`{% if ... %}name{% endif %}`) that rendered
    # empty resolves to an existing directory — nothing to write.
    if os.path.isdir(outfile):
        logger.debug("The resulting file name is empty: %s", outfile)
        return

    if skip_if_file_exists and os.path.exists(outfile):
        logger.debug("The resulting file already exists: %s", outfile)
        return

    if is_binary(infile):
        logger.debug("Copying binary %s to %s without rendering", infile, outfile)
        shutil.copyfile(infile, outfile)
    else:
        # Force fwd slashes on Windows for get_template — a by-design Jinja issue
        infile_fwd_slashes = infile.replace(os.path.sep, "/")

        try:
            tmpl = env.get_template(infile_fwd_slashes)
        except TemplateSyntaxError as exception:
            # Disable translated so that the printed exception contains verbose
            # information about the syntax error location
            exception.translated = False
            raise
        rendered_file = tmpl.render(**jinja_context)

        # Detect the original file's newline style so rendering doesn't
        # convert it; newline='' disables translation while reading.
        with open(infile, encoding="utf-8", newline="") as rd:
            rd.readline()  # Read the first line to load the 'newlines' value
            newline = newline_override or rd.newlines

        logger.debug("Writing contents to file %s", outfile)
        with open(outfile, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(rendered_file)

    # Apply the template file's permissions to the output file
    shutil.copymode(infile, outfile)


def _run_hook_guarded(
    hook_name, hooks_dir, project_dir, jinja_context, env, delete_project_on_failure
):
    """Run a hook, cleaning up the project directory if the hook fails."""
    try:
        run_hook(hook_name, hooks_dir, project_dir, jinja_context, env)
    except FailedHookError:
        if delete_project_on_failure:
            rmtree(project_dir)
        logger.error(
            "Stopping generation because %s hook script didn't exit successfully",
            hook_name,
        )
        raise


def forge(
    template,
    context,
    output_dir=".",
    *,
    context_key="forge",
    extensions=(),
    remove_file_extension=".jinja2",
    copy_without_render=(),
    overwrite_if_exists=False,
    skip_if_file_exists=False,
    accept_hooks=True,
    keep_project_on_failure=False,
    newline=None,
    env_options=None,
    sandboxed=False,
):
    """Render a project from a template directory into ``output_dir``.

    :param template: Directory containing the templated (``{{ ... }}``)
        project directory, and optionally a ``hooks/`` directory.
    :param context: The template context. Exposed to Jinja under
        ``context_key``, e.g. ``{{ forge.project_id }}``.
    :param output_dir: Where to output the generated project dir into.
    :param context_key: Top-level Jinja variable name for the context.
    :param extensions: Jinja2 extensions, as import-path strings or classes.
    :param remove_file_extension: Strip this extension from rendered file
        names, e.g. ``".jinja2"`` (the default), or any of several, e.g.
        ``(".jinja2", ".j2")``. Pass ``None`` or ``()`` to disable stripping.
    :param copy_without_render: fnmatch patterns (relative to the template
        directory) for files/dirs to copy verbatim instead of rendering.
    :param overwrite_if_exists: Render into the output directory even if it
        already exists.
    :param skip_if_file_exists: Skip files that already exist in the output.
    :param accept_hooks: Run ``pre_gen_project``/``post_gen_project`` hooks.
        Set ``False`` for template sources you don't trust to run code.
    :param keep_project_on_failure: Keep the generated directory even when
        generation fails.
    :param newline: Force this newline style on rendered files instead of
        detecting it per template file.
    :param env_options: Extra keyword arguments for ``jinja2.Environment``.
    :param sandboxed: Render with ``jinja2.sandbox.SandboxedEnvironment``
        instead of the plain ``Environment``. Use alongside
        ``accept_hooks=False`` for template sources you don't trust.
    :return: Path to the generated project directory.
    """
    repo_dir = os.path.abspath(template)
    output_dir = os.path.abspath(output_dir)
    template_dir = find_template(repo_dir)
    hooks_dir = os.path.join(repo_dir, "hooks")
    logger.debug("Generating project from %s...", template_dir)

    remove_file_extension = _normalize_extensions(remove_file_extension)

    jinja_context = {context_key: context}
    env = create_environment(
        extensions=extensions, env_options=env_options, sandboxed=sandboxed
    )

    unrendered_dir = os.path.basename(template_dir)
    try:
        project_dir, output_directory_created = _render_and_create_dir(
            unrendered_dir, jinja_context, output_dir, env, overwrite_if_exists
        )
    except UndefinedError as err:
        msg = f"Unable to create project directory '{unrendered_dir}'"
        raise UndefinedVariableInTemplateError(msg, err) from err

    # We want the Jinja path and the OS paths to match, so we CD to the
    # template folder and set Jinja's path to '.'; the target folder
    # (project_dir) is used as an absolute path.
    project_dir = os.path.abspath(project_dir)
    logger.debug("Project directory is %s", project_dir)

    # If we created the output directory, it's ok to remove it if rendering fails
    delete_project_on_failure = output_directory_created and not keep_project_on_failure

    if accept_hooks:
        _run_hook_guarded(
            "pre_gen_project",
            hooks_dir,
            project_dir,
            jinja_context,
            env,
            delete_project_on_failure,
        )

    with work_in(template_dir):
        env.loader = FileSystemLoader([".", "../templates"])

        for root, dirs, files in os.walk("."):
            # Separate copy-only dirs from render dirs: ``os.walk`` must not
            # descend into unrendered directories, since they are copied whole.
            copy_dirs = []
            render_dirs = []

            for d in dirs:
                d_ = os.path.normpath(os.path.join(root, d))
                # Check the full (relative) path, as that is how patterns are
                # given in ``copy_without_render``
                if _is_copy_only_path(d_, copy_without_render):
                    logger.debug("Found copy only path %s", d)
                    copy_dirs.append(d)
                else:
                    render_dirs.append(d)

            for copy_dir in copy_dirs:
                indir = os.path.normpath(os.path.join(root, copy_dir))
                outdir = os.path.normpath(os.path.join(project_dir, indir))
                outdir = env.from_string(outdir).render(**jinja_context)
                logger.debug("Copying dir %s to %s without rendering", indir, outdir)

                if os.path.isdir(outdir):
                    shutil.rmtree(outdir)
                shutil.copytree(indir, outdir)

            # Mutate ``dirs`` so the walk only recurses into render dirs
            dirs[:] = render_dirs
            for d in dirs:
                unrendered_subdir = os.path.join(project_dir, root, d)
                try:
                    _render_and_create_dir(
                        unrendered_subdir,
                        jinja_context,
                        output_dir,
                        env,
                        overwrite_if_exists,
                    )
                except UndefinedError as err:
                    if delete_project_on_failure:
                        rmtree(project_dir)
                    _dir = os.path.relpath(unrendered_subdir, output_dir)
                    msg = f"Unable to create directory '{_dir}'"
                    raise UndefinedVariableInTemplateError(msg, err) from err

            for f in files:
                infile = os.path.normpath(os.path.join(root, f))
                if _is_copy_only_path(infile, copy_without_render):
                    outfile_rendered = env.from_string(infile).render(**jinja_context)
                    outfile = os.path.join(project_dir, outfile_rendered)
                    logger.debug(
                        "Copying file %s to %s without rendering", infile, outfile
                    )
                    shutil.copyfile(infile, outfile)
                    shutil.copymode(infile, outfile)
                    continue
                try:
                    _generate_file(
                        project_dir,
                        infile,
                        jinja_context,
                        env,
                        remove_file_extension,
                        skip_if_file_exists,
                        newline,
                    )
                except UndefinedError as err:
                    if delete_project_on_failure:
                        rmtree(project_dir)
                    msg = f"Unable to create file '{infile}'"
                    raise UndefinedVariableInTemplateError(msg, err) from err

    if accept_hooks:
        _run_hook_guarded(
            "post_gen_project",
            hooks_dir,
            project_dir,
            jinja_context,
            env,
            delete_project_on_failure,
        )

    return Path(project_dir)
