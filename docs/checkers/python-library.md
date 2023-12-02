Checker Script Python Library
=============================

The **Checker Script Python Library** provides facilities to write [Checker Scripts](index.md) in
Python 3.

It takes care of:

* Communication with the Checker Master
* Starting check steps
* Command line argument handling
* Configuring logging to send messages to the Master
* Setup of default timeouts for Python sockets, [urllib3](https://urllib3.readthedocs.io), and
  [Requests](https://requests.readthedocs.io)
* Handling of common connection exceptions and converting them to a DOWN result

This means that you do **not** have to catch timeout exceptions and can just let the library take care of
them.

Installation
------------
To use the library, you must have the `ctf_gameserver.checkerlib` package available to your Python
installation. That package is self-contained and does not require any external dependencies.

One option to do that would be to clone the [CTF Gameserver
repository](https://github.com/fausecteam/ctf-gameserver) and create a symlink called `ctf_gameserver` to
`src/ctf_gameserver`.

Another option would be to install CTF Gameserver (preferably to a virtualenv) by running `pip install .`
in the repository directory.

API
---
To create a Checker Script, create a subclass of `checkerlib.BaseChecker` implementing the following methods:

* `place_flag(self, tick: int) -> checkerlib.CheckResult`: Called once per Script execution to place a flag
  for the current tick. Use `checkerlib.get_flag(tick)` to get the flag.
* `check_service(self) -> checkerlib.CheckResult`: Called once per Script execution to determine general
  service health.
* `check_flag(self, tick: int) -> checkerlib.CheckResult`: Determine if the flag for the given tick can be
  retrieved. Use `checkerlib.get_flag(tick)` to get the flag to check for. Called multiple times per Script
  execution, for the current and preceding ticks.

In your `__main__` code, call `checkerlib.run_check()` with your class as argument. The library will take
care of calling your methods, merging the results, and submitting them to the Checker Master.

### Functions
* `get_flag(tick: int) -> str`: Get the flag for the given tick (for the checked team).
* `set_flagid(data: str) -> None`: Store the Flag ID for the current tick.
* `store_state(key: str, data: Any) -> None`: Store arbitrary Python data persistently across runs.
* `load_state(key: str) -> Any`: Retrieve data stored through `store_state()`.
* `run_check(checker_cls: Type[BaseChecker]) -> None`: Start the check.

### Classes
* The `checkerlib.BaseChecker` class provides the following attributes:
    * `self.ip`: IP address of the checked team (may be IPv4 or IPv6, depending on your CTF)
    * `self.team`: (Net) number of the checked team
* `checkerlib.CheckResult` provides the following constants to express check results, [see general
  docs](index.md#check-results) for their semantics:
    * `CheckResult.OK`
    * `CheckResult.DOWN`
    * `CheckResult.FAULTY`
    * `CheckResult.FLAG_NOT_FOUND`

### Minimal Example
```py
#!/usr/bin/env python3

from ctf_gameserver import checkerlib

class MinimalChecker(checkerlib.BaseChecker):
    def place_flag(self, tick):
        return checkerlib.CheckResult.OK

    def check_service(self):
        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        return checkerlib.CheckResult.OK

if __name__ == '__main__':
    checkerlib.run_check(MinimalChecker)
```

For a complete, but still simple, Checker Script see `examples/checker/example_checker.py` in the
[CTF Gameserver repository](https://github.com/fausecteam/ctf-gameserver).

Local Execution
---------------
When running your Checker Script locally, just pass your service IP, the tick to check (starting from 0),
and a dummy team ID as command line arguments:

```sh
./checkerscript.py ::1 10 0
```

The library will print messages to stdout and generate dummy flags when launched without a Checker Master.
State stored will be persisted in a file called `_state.json` in the current directory in that case.
