"""Pure workflow-builder compatibility rules - no I/O, no ORM, no FastAPI.

The format service is reached only through a `FormatLookup` the caller passes in, so every
rule here is a plain function over plain data and directly unit-testable.
"""
