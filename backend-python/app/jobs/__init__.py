"""Entry points for scheduled jobs - like the routers in app.api, but started by a scheduler
instead of an HTTP request. Each job is a module run as `python -m app.jobs.<name>`: it does
one task through an application service and exits, 0 on success."""
