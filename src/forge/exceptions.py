"""All exceptions raised by the Forge engine."""


class ForgeError(Exception):
    """Base exception for all Forge errors."""


class TemplateDirNotFoundError(ForgeError):
    """Raised when the template repo contains no ``{{ ... }}`` directory."""


class AmbiguousTemplateDirError(ForgeError):
    """Raised when the template repo contains multiple ``{{ ... }}`` directories."""


class OutputDirExistsError(ForgeError):
    """Raised when the rendered output directory already exists."""


class FailedHookError(ForgeError):
    """Raised when a hook script fails."""


class UnknownExtensionError(ForgeError):
    """Raised when a Jinja extension cannot be imported."""


class UndefinedVariableInTemplateError(ForgeError):
    """Raised when a template references a variable missing from the context."""

    def __init__(self, message, error):
        self.message = message
        self.error = error
        super().__init__(f"{message}. Error message: {error.message}")
