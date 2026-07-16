"""Jinja2 environment construction."""

from jinja2 import Environment, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from forge.exceptions import UnknownExtensionError


def create_environment(extensions=(), env_options=None, sandboxed=False):
    """Create a strict Jinja2 environment for rendering a template.

    :param extensions: Jinja2 extensions, as import-path strings or classes.
    :param env_options: Extra keyword arguments passed to ``jinja2.Environment``
        (e.g. custom delimiters). ``keep_trailing_newline`` defaults to True.
    :param sandboxed: Use ``jinja2.sandbox.SandboxedEnvironment`` instead of the
        plain ``Environment``, restricting the attributes/methods template code
        can reach (blocks the usual ``__class__``/``__mro__``/``__globals__``
        gadget chains). Use for templates from untrusted sources.
    """
    options = {"keep_trailing_newline": True}
    if env_options:
        options.update(env_options)

    environment_cls = SandboxedEnvironment if sandboxed else Environment

    try:
        return environment_cls(
            undefined=StrictUndefined,
            extensions=list(extensions),
            **options,
        )
    except ImportError as err:
        raise UnknownExtensionError(f"Unable to load extension: {err}") from err
