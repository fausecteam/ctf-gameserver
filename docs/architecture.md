Architecture
============

Command & Control
-----------------
All integration between CTF Gameserver's components happens through a shared PostgreSQL database.
The **Controller** orchestrates all actions performed by the other components based on its system clock.
The system clock of the other components does not affect the competition's progress.

Ticks
-----
The competition is divided into discrete time frames of a fixed duration. These are called **ticks** and
can be seen as rounds. Checking and scoring happen once per tick. Tick numbers start at zero.

Anatomy of a Tick
-----------------
The **Controller** checks the clock and notices that it is time to start a new tick. It increments the
current tick and creates the flags for the new tick in the database.

Each **Checker Master** belongs to one service. It regularly checks the database for flags to be placed.
For each flag (i.e. team), it launches the service's Checker Script as a separate process. If any Scripts
from previous ticks are still running, they get terminated. Checkers can be horizontally scaled by running
multiple Master instances per service.

**Checker Scripts** have to be specifically created for the competition's individual services. Helper
libraries are currently provided for Python and Go, but any language can be used to implement the Checker
Script IPC protocol. For details, see the [documentation on Checkers](checkers/index.md). The status for the
tick (OK, down, etc.) is determined from the outcome of placing the new flag and retrieving flags from
previous ticks. The resulting status gets written to the database.

At any time, teams can connect to the **Submission** server and submit flags they captured from other teams.
The submission protocol is described in the [Submission documentation](submission.md). For flags that are
valid and haven't been submitted by the same team before, a capture event is stored in the database. 
Submission servers can be horizontally scaled by running multiple instances. For an example configuration
with multiple instances behind a single port, see the
[Submission installation docs](installation.md#submission).

At the start of the next tick, the **Controller** updates the scoreboard in the database by calculating the
scores for the old tick based on status checks and capture events.

Flags
-----
The string representation of a flag can always be generated from its database entry and the competition's
flag secret. It consists of a configurable static prefix, followed by the encoded flag data and a
[MAC](https://en.wikipedia.org/wiki/Message_authentication_code).

Using a prefix of `FAUST_`, a valid flag could look like this: `FAUST_Q1RGLRml7uVTRVJBRXdsFhEI3jhxey9I`

Flag IDs
--------
In some cases, you want to provide teams with an identifier which helps retrieve an individual Flag. For
example, consider a case where an exploit allows read access to a key/value store. To get Flag data, teams
still have to know the keys under which valid Flags are stored. This can also help to reduce load on your
service, because keys don't have to be brute-forced and a listing is not necessary.

For this purpose, we provide the concept of **Flag IDs**. They are purely optional, not every service needs
to provide them.

Team Numbers
------------
Teams have two different numbers, ID and Net Number.

The **Team ID** is the primary key of the team's database entry. It is usually assigned in ascending order by
registration time and only used internally.

The **Team Net Number** is used to construct the team's IP address range (e.g. `10.66.<net-number>.0/24`).
It is assigned randomly and sometimes also just called "Team Number". It aims to prevent correlation between
the teams' registration order and address range, making it harder to target a specific team. This means teams
should only know their own assignment.

teams.json
----------
Flag IDs and the set of actually assigned Net Numbers are generally unknown to teams. This information is
provided to teams as JSON by the CTF Gameserver web component under the path `/competition/teams.json` in the
following format:

    {
        "teams": [123, 456, 789],
        "flag_ids": {
            "service1": {
    			// Keys are net numbers from above as strings
                "123": ["abc123", "def456"],
                "789": ["xxx", "yyy"]
            }
        }
    }
