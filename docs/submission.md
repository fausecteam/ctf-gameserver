Flag Submission
===============

In order to score points for captured flags, the flags are submitted over a simple TCP-based plaintext
protocol. That protocol was agreed upon by the organizers of several A/D CTFs in [this GitHub
discussion](https://github.com/enowars/specification/issues/14).

The following documentation describes the generic, agreed-upon protocol. CTF Gameserver itself uses a more
restricted flag format, it will for example never generate non-ASCII flags. For details on how CTF Gameserver
creates flags, see [flag architecture](architecture.md#flags).

Definitions
-----------
* **Whitespace** consists of one or more space (ASCII `0x20`) and/or tab (ASCII `0x09`) characters.
* **Newline** is a single `\n` (ASCII `0x0a`) character.
* **Flags** are sequences of arbitrary characters, except whitespace and newlines.

Protocol
--------
The client connects to the server on a TCP port specified by the respective CTF. The server MAY send a
welcome banner, consisting of anything except two subsequent newlines. The server MUST indicate that the
welcome sequence has finished by sending two subsequent newlines (`\n\n`).

If a general error with the connection or its configuration renders the server inoperable, it MAY send an
arbitrary error message and close the connection before sending the welcome sequence. The error message MUST
NOT contain two subsequent newlines.

To submit a flag, the client MUST send the flag followed by a single newline.
The server's response MUST consist of:

1. A repetition of the submitted flag
2. Whitespace
3. One of the response codes defined below
4. Optionally: Whitespace, followed by a custom message consisting of any characters except newlines
5. Newline

During a single connection, the client MAY submit an arbitrary number of flags. When the client is finished,
it MUST close the TCP connection. The server MAY close the connection on inactivity for a certain amount of
time.

The client MAY send flags without waiting for the welcome sequence or responses to previously submitted
flags. The server MAY send the responses in an arbitrary order; the connection between flags and responses
can be derived from the flag repetition in the response.

Response Codes
--------------
* `OK`: The flag was valid, has been accepted by the server, and will be considered for scoring.
* `DUP`: The flag was already submitted before (by the same team).
* `OWN`: The flag belongs to (i.e. is supposed to be protected by) the submitting team.
* `OLD`: The flag has expired and cannot be submitted anymore.
* `INV`: The flag is not valid.
* `ERR`: The server encountered an internal error. It MAY close the TCP connection. Submission may be retried
  at a later point.

The server MUST implement `OK`, `INV`, and `ERR`. Other response codes are optional. The client MUST be able
to handle all specified response codes. For extensibility, the client SHOULD be able to handle any response
codes consisting of uppercase ASCII letters.

Example
-------
"C:" and "S:" indicate lines sent by the client and server, respectively. Each line includes the terminating
newline.

```
S: Welcome to Example CTF flag submission! 🌈
S: Please submit one flag per line.
S:
C: FLAG{4578616d706c65}
S: FLAG{4578616d706c65} OK
C: 🏴‍☠️
C: FLAG{🤔🧙‍♂️👻💩🎉}
S: FLAG{🤔🧙‍♂️👻💩🎉} DUP You already submitted this flag
S: 🏴‍☠️ INV Bad flag format
```
