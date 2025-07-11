---
applyTo: "**"
---

This repository implements a Gameserver for attack-defense CTFs (IT security competitions).
Development happens with a specific focus on correctness, security, and long-term maintainability.

## Project Architecture
The software consists of multiple components, all written in Python:

* Web: A Django-based web application for team registration, scoreboards, and simple hosting of informational pages. It also contains the model files, which define the database structure.
* Controller: Coordinates the progress of the competition, e.g. the current tick and flags to be placed.
* Checker: Place and retrieve flags and test the service status on all teams' Vulnboxes. The Checker Master launches Checker Scripts, which are individual to each service.
* Checkerlib: Libraries to assist in developing Checker Scripts. Currently, Python and Go are supported.
* Submission: Server to submit captured flags to.
* VPN Status: Optional helper that collects statistics about network connectivity to teams.

More information on the architecture can be found in the `docs` directory, especially in `docs/index.md` and `docs/architecture.md`.

## General Conduct
* Do not make more changes than necessary at once.
* Don't be too eager. Prefer a step-wise, iterative approach.
* In doubt, ask the user for more details or clarification. Do not make too many assumptions.
* In the (text-based) chat, provide short, precise responses.

## Coding Style
* Code mostly follows PEP 8 with some minor deviations.
* Line length is 109 characters plus newline.
* Let yourself be guided by the style of the existing codebase.
* Especially when PEP 8 leaves multiple options, use the style that is already present in the codebase.
* Variable names should be descriptive, even if that makes them longer.
* For regular strings, single quotes are preferred.
* Doc strings use Google style with double quotes, but with a newline after the opening `"""`.
* We use a combination of pylint and pycodestyle for linting, as well as Bandit for security checks. All linters can be invoked through `make lint`.
* The pylint config is at `src/pylintrc`, the pycodestyle config is contained in `tox.ini`.

## Dependencies
* The currently supported minimal Python version is 3.13.
* We try to keep our external dependencies rather minimal.
* We only use Python dependencies which are also available in the official Debian repositories, in versions compatible with the packaged ones.
* In doubt, do not concern yourself with dependency management, but just tell the user what you need.
* Never introduce a new dependency without asking for confirmation.
* Frontend dependencies (CSS, JavaScript, etc.) are installed through the project's Makefile. Do not try to be clever about this.

## Database Access
* The database schema is defined through the Django models from the Web component. Other components also access these database tables.
* In the Web component, the Django ORM is used for database access.
* Other components directly use SQL statements.
* While only PostgreSQL is used in production, SQLite is used for development and testing.
* This means SQL statements must generally be compatible with both PostgreSQL and SQLite. For certain cases, there is some hacky compatibility code in `src/ctf_gameserver/lib/database.py`.

## Django Instructions
For the Django-based Web component (`src/ctf_gameserver/web`):

* We do not support long-living databases and therefore do not need to do database migrations. Never generate migration files.
* We generally use function-based views so far. Unless they provide a clear benefit, do not introduce class-based views to the codebase.
* Primarily for historic reasons, the URLconf uses regex-based patterns (`re_path` instead of `path`). This is fine, no need to change it.

## Testing
* Tests are executed using pytest through `make test` or by invoking `pytest` directly.
* Test cases are standard Python unit tests. pytest is only used as a test runner, not as a framework for writing tests.
* Even for the non-Web components, the test database is provided by invoking Django's database setup code. This is handled by the `DatabaseTestCase` base class.
* Consequently, test data is always provided through Django fixtures.
* There currently are no test cases for the Web component. When writing Django code, do not add tests unless explicitly asked to.
