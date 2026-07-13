"""Jinja2 environment construction."""

from jinja2 import Environment, StrictUndefined

from forge.exceptions import UnknownExtensionError


def create_environment(extensions=(), env_options=None):
    """Create a strict Jinja2 environment for rendering a template.

    :param extensions: Jinja2 extensions, as import-path strings or classes.
    :param env_options: Extra keyword arguments passed to ``jinja2.Environment``
        (e.g. custom delimiters). ``keep_trailing_newline`` defaults to True.
    """
    options = {"keep_trailing_newline": True}
    if env_options:
        options.update(env_options)

    try:
        return Environment(
            undefined=StrictUndefined,
            extensions=list(extensions),
            **options,
        )
    except ImportError as err:
        raise UnknownExtensionError(f"Unable to load extension: {err}") from err
