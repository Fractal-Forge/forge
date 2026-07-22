"""Jinja2 extensions shipped with forge.

``StringOperationsExtension`` provides the generic name-casing filters the
Fractal Forge generator templates use — ``snake`` / ``camel`` / ``dash`` /
``lower`` / ``upper`` / ``slug``. These are cookiecutter-level string helpers
(no domain knowledge), which is why they live in the open engine rather than in
any private generator.

The implementations are intentionally byte-for-byte identical to the ones the
generator historically shipped: templates depend on the exact casing behaviour
(e.g. how ``snake`` splits existing CamelCase), so any divergence would silently
change generated output. Treat the behaviour as frozen; the tests lock it.

The ``slug`` filter needs ``python-slugify``. It is imported lazily so the rest
of the extension works without it; install the optional extra to use ``slug``::

    pip install "fractal-forge[filters]"
"""

import re

from jinja2.ext import Extension


class StringOperationsExtension(Extension):
    """Register the string-casing filters on the Jinja2 environment."""

    def __init__(self, environment):
        super().__init__(environment)
        environment.filters["snake"] = StringOperationsExtension.snake
        environment.filters["camel"] = StringOperationsExtension.camel
        environment.filters["dash"] = StringOperationsExtension.dash
        environment.filters["lower"] = StringOperationsExtension.lower
        environment.filters["upper"] = StringOperationsExtension.upper
        environment.filters["slug"] = StringOperationsExtension.slug

    @staticmethod
    def snake(value: str) -> str:
        value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
        value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()
        value = (
            StringOperationsExtension.lower(value).replace(" ", "_").replace("-", "_")
        )
        return re.sub(r"_+", "_", value).strip("_")

    @staticmethod
    def camel(value: str) -> str:
        value = StringOperationsExtension.snake(value)
        return "".join(word.title() for word in value.split("_"))

    @staticmethod
    def dash(value: str) -> str:
        value = StringOperationsExtension.snake(value)
        return value.replace("_", "-")

    @staticmethod
    def lower(value: str) -> str:
        return value.lower()

    @staticmethod
    def upper(value: str) -> str:
        return value.upper()

    @staticmethod
    def slug(value: str) -> str:
        try:
            from slugify import slugify
        except ImportError as exc:  # pragma: no cover - guarded import
            raise RuntimeError(
                "the 'slug' filter requires python-slugify; install the extra: "
                'pip install "fractal-forge[filters]"'
            ) from exc
        return slugify(value)
