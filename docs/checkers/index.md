Checkers
========

**Checkers** connect to the services of all teams. They verify that the service is working properly, and
place and retrieve flags. An individual **Checker Script** exists per service, which implements
service-specific functionality. During the competition, Checker Scripts are launched by the **Checker
Master**.

Having robust checker scripts is essential for a fun competition. Checker Scripts will encounter different
kinds of half-broken services, slow networks, unreachable hosts, and lots of other things. They should always
return a result and never exit unexpectedly (e.g. due to an uncaught exception). Make sure to test your
Checker Scripts under various conditions.

Checker Scripts should behave like a regular user of the respective service and not be trivially
distinguishable from attackers. They also need to be able to recover from partial data loss on the Vulnboxes.

Checker Script libraries
------------------------
Libraries in the following languages are currently available to assist you in developing Checker Scripts:

* [Python](python-library.md)
* [Go](go-library.md)

Execution Model
---------------
For each service and team, one Checker Script gets executed per tick. The Checker Master launches the Scripts
as individual processes and communicates with them through an [IPC protocol](#ipc-protocol). This
architecture was chosen since Checker Scripts deal with a lot of untrusted input, and should therefore not
have direct access to the Gameserver database.

The same Script may run in parallel for different teams. There may be multiple Masters (on different
hosts), so checks for the same team may be started by different Masters in different ticks. Therefore, [a
special API](#persistent-state) has to be used to keep state across ticks.

Checker Scripts should perform the following steps in each tick:

1. Place new flag for the current tick
2. Check general service availability
3. Retrieve flag of the current and five previous ticks

The Checker Script has to determine a single result from all of these steps. That means that if any of them
fails, the service shall not be considered OK. If a step fails, the remaining ones do not need to be
performed.

Arguments
---------
Checker Scripts are started with the following command line arguments:

```sh
checkerscript <ip> <tick> <team>
```

`<ip>` is the address of the team to be checked, `<tick>` is the current tick number and `<team>` is the ID
of the team to be checked.

Check Results
-------------
Each check reports one of the following results:

* OK: Everything working fine
* DOWN: Service not running or another error in the network connection, e.g. a timeout or connection abort
* FAULTY: Service is available, but not behaving as expected
* FLAG_NOT_FOUND: Service is behaving as expected, but a flag could not be retrieved
* RECOVERING: Service is behaving as expected, at least one flag could be retrieved, but one or more from
  previous ticks could not (usually not issued by a Checker Script itself, but handled by [a
  library](#checker-script-libraries))

If a Checker Script exits without reporting a result (e.g. dying due to an exception), no results will be
stored for the tick (displayed as "Not checked" by the Gameserver frontend).

The Script's exit code does *not* influence the check result.

Error Handling
--------------
If errors occur while establishing a connection or sending requests, the service should be considered
DOWN. These errors have to be handled by Checker Scripts, but [libraries](#checker-script-libraries)
usually assist with that.

Issues with the service itself (e.g. unexpected or missing output to requests) must be detected by Checker
Scripts and lead to a FAULTY result.

This means that a proper Checker Script should never exit unexpectedly (with an exception, panic, or
similar).

Logging
-------
It is generally desirable to add *lots of* logging to Checker Scripts. For unified access to logs from
different Master instances, log messages get forwarded through the Master and stored centrally (see
[Checker logging docs](../observability.md#checkers)).

Stdout and stderr from Checker Scripts are captured as well, but will lack metadata such as log level or
source code line.

Persistent State
----------------
Through special load and store commands to the Master, Checker Scripts can keep persistent state cross
ticks. State is identified by a string key and must consist of valid UTF-8 data. However, [Checker Script
libraries](#checker-script-libraries) may allow to store arbitrary data and handle serialization. State is
kept separately per team (and service), but not separated by tick. The Master makes sure that state stored in
one tick can be loaded in subsequent ones, regardless of the Master instances involved.

Flag IDs
--------
See ["Flag IDs" on Architecture page](../architecture.md#flag-ids).

One ID can be stored per Flag by the Checker Script. Flag IDs must be UTF-8 strings with a maximum length of
100 characters.

IPC Protocol
------------
All communication with the Master is initiated by the Checker Script. The Master will handle the Script's
request and return a result synchronously.

When launching a Checker Script, the Master passes two Unix pipes as additional open file descriptors to
the new process. Requests to the Master can be sent on file descriptor 4, responses can be read from file
descriptor 3. Messages are JSON objects sent on a single line.
