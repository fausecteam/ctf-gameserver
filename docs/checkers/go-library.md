Checker Script Go Library
=========================

The **Checker Script Go Library** provides facilities to write [Checker Scripts](index.md) in Go.

It takes care of:

* Communication with the Checker Master
* Starting check steps
* Command line argument handling
* Configuring logging to send messages to the Master
* Setup of default timeouts for "net/http"
* Handling of common connection errors and converting them to a DOWN result

This means that you do **not** have to handle timeout errors and can just let the library take care of them.

Installation
------------
The library uses Go modules and can be imported via "github.com/fausecteam/ctf-gameserver/go/checkerlib"

API
---
To create a Checker Script, implement the `checkerlib.Checker` interface with the following methods:

* `PlaceFlag(ip string, team int, tick int) (checkerlib.Result, error)`: Called once per Script execution to
  place a flag for the current tick. Use `checkerlib.GetFlag(tick, nil)` to get the flag and (optionally)
  `SetFlagID(data string)` to store the flag ID.
* `CheckService(ip string, team int) (Result, error)`: Called once per Script execution to determine general
  service health.
* `CheckFlag(ip string, team int, tick int) (checkerlib.Result, error)`: Determine if the flag for the given
  tick can be retrieved. Use `checkerlib.GetFlag(tick, nil)` to get the flag to check for. Called multiple
  times per Script execution, for the current and preceding ticks.

In your `main()`, call `checkerlib.RunCheck()` with your implementation as argument. The library will take
care of calling your methods, merging the results, and submitting them to the Checker Master.

### Persistent State
* `StoreState(key string, data interface{})`: Store data persistently across runs (serialized as JSON).
  Data is stored per service and team with the given key as an additional identifier.
* `LoadState(key string, data interface{}) bool`: Retrieve data stored through `StoreState()` (deserialized into
  `data`). Returns `true` if any state was found.

### Helper functions
* `Dial(network, address string) (net.Conn, error)`: Calls `net.DialTimeout()` with an appropriate timeout.

### Constants
* `Timeout`: Default timeout used when connecting to services. In case you cannot use the standard functions
  of "net/http" (those using `DefaultClient`/`DefaultTransport`) or `checkerlib.Dial()`.
* Check results, [see general docs](index.md#check-results) for their semantics:
    * `ResultOk`
    * `ResultDown`
    * `ResultFaulty`
    * `ResultFlagNotFound`

### Minimal Example
```go
package main

import (
	"github.com/fausecteam/ctf-gameserver/go/checkerlib"
)

func main() {
	checkerlib.RunCheck(checker{})
}

type checker struct{}

func (c checker) PlaceFlag(ip string, team int, tick int) (checkerlib.Result, error) {
	return checkerlib.ResultOk, nil
}

func (c checker) CheckService(ip string, team int) (checkerlib.Result, error) {
	return checkerlib.ResultOk, nil
}

func (c checker) CheckFlag(ip string, team int, tick int) (checkerlib.Result, error) {
	return checkerlib.ResultOk, nil
}
```

For a complete, but still simple, Checker Script see `examples/checker/example_checker_go` in the [CTF
Gameserver repository](https://github.com/fausecteam/ctf-gameserver).

Local Execution
---------------
When running your Checker Script locally, just pass your service IP, the tick to check (starting from 0),
and a dummy team ID as command line arguments:

```sh
go build && ./checkerscript ::1 10 0
```

The library will print messages to stderr and generate dummy flags when launched without a Checker Master.
State stored will be persisted in a file called `_state.json` in the current directory in that case.
