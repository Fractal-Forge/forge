"""Forge — minimal Jinja2 rendering engine for Fractal Forge generator templates.

Derived from Cookiecutter (BSD-3-Clause), reduced to the feature set the
Fractal Forge generator actually uses: the caller supplies the full context,
so there is no context file, no prompting, no user config, no VCS cloning
and no replay.
"""

from forge.exceptions import (
    AmbiguousTemplateDirError,
    FailedHookError,
    ForgeError,
    OutputDirExistsError,
    TemplateDirNotFoundError,
    UndefinedVariableInTemplateError,
    UnknownExtensionError,
)
from forge.main import forge

__version__ = "0.1.0"

__all__ = [
    "forge",
    "ForgeError",
    "TemplateDirNotFoundError",
    "AmbiguousTemplateDirError",
    "OutputDirExistsError",
    "FailedHookError",
    "UnknownExtensionError",
    "UndefinedVariableInTemplateError",
    "__version__",
]
