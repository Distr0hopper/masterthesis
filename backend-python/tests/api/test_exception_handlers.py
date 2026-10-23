"""Every business-rule exception has an HTTP mapping - one left out would reach the client
as a 500, as if the server had crashed, instead of saying which rule refused the request."""

import importlib
import inspect
import pkgutil

import pytest

import app.application.exception
import app.domain.exception
from app.main import app as fastapi_app

#: the modules whose exceptions a request may raise on purpose
_MODULES = [
    *(f"app.application.exception.{m.name}" for m in pkgutil.iter_modules(app.application.exception.__path__)),
    *(f"app.domain.exception.{m.name}" for m in pkgutil.iter_modules(app.domain.exception.__path__)),
    "app.domain.composite.lifecycle",
    "app.api.exception.exceptions",
]


def _business_exceptions() -> list[type[Exception]]:
    found: dict[str, type[Exception]] = {}
    for module_name in _MODULES:
        module = importlib.import_module(module_name)
        for _, member in inspect.getmembers(module, inspect.isclass):
            if issubclass(member, Exception) and member.__module__ == module_name:
                found[f"{module_name}.{member.__name__}"] = member
    return [found[key] for key in sorted(found)]


def _has_subclasses(exception: type[Exception]) -> bool:
    return any(other is not exception and issubclass(other, exception) for other in _business_exceptions())


@pytest.mark.parametrize(
    "exception",
    # a base class only groups its subclasses - they are what gets raised and mapped
    [e for e in _business_exceptions() if not _has_subclasses(e)],
    ids=lambda e: e.__name__,
)
def test_every_business_exception_has_a_handler(exception: type[Exception]) -> None:
    handled = [base for base in exception.__mro__ if base in fastapi_app.exception_handlers]
    assert handled and handled[0] is not Exception, f"{exception.__name__} has no exception handler"
