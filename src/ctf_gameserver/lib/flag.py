import base64
import binascii
import hashlib
from hmac import compare_digest
import struct
import time
import zlib

# Length of the MAC (in bytes)
MAC_LEN = 9
# Length of the payload (in bytes)
PAYLOAD_LEN = 8
# timestamp + team + service + payload
DATA_LEN = 4 + 2 + 1 + PAYLOAD_LEN
# Flag validity in seconds
VALID = 900


def generate(team_net_no, service_id, secret, prefix='FLAG_', payload=None, timestamp=None):
    """
    Generates a flag for the given arguments. This is deterministic and should always return the same
    result for the same arguments (and the same time, if no timestamp is explicitly specified).

    Args:
        team_net_no: Net number of the team protecting this flag
        service_id: ID of the service this flag belongs to
        payload: 8 bytes of data to store in the flag, defaults to zero-padded
                 CRC32(timestamp, team, service)
        timestamp: Timestamp at which the flag expires, defaults to 15 minutes in the future
    """

    if timestamp is None:
        timestamp = time.time() + VALID

    if team_net_no > 65535:
        raise ValueError('Team net number must fit in 16 bits')
    protected_data = struct.pack("!i H c", int(timestamp), team_net_no, bytes([service_id]))

    if payload is None:
        payload = struct.pack("!I I", zlib.crc32(protected_data), 0)
    if len(payload) != PAYLOAD_LEN:
        raise ValueError('Payload {} must be {:d} bytes long'.format(repr(payload), PAYLOAD_LEN))

    protected_data += payload
    mac = _gen_mac(secret, protected_data)

    return prefix + base64.b64encode(protected_data + mac).decode('ascii')


def verify(flag, secret, prefix='FLAG_'):
    """
    Verfies flag validity and returns data from the flag.
    Will raise an appropriate exception if verification fails.

    Returns:
        Data from the flag as a tuple of (team, service, payload, timestamp)
    """

    if not flag.startswith(prefix):
        raise InvalidFlagFormat()

    try:
        raw_flag = base64.b64decode(flag[len(prefix):])
    except binascii.Error:
        raise InvalidFlagFormat()

    try:
        protected_data, flag_mac = raw_flag[:DATA_LEN], raw_flag[DATA_LEN:]
    except IndexError:
        raise InvalidFlagFormat()

    mac = _gen_mac(secret, protected_data)
    if not compare_digest(mac, flag_mac):
        raise InvalidFlagMAC()

    timestamp, team, service = struct.unpack("!i H c", protected_data[:7])
    payload = protected_data[7:]
    if time.time() - timestamp > 0:
        raise FlagExpired(time.time() - timestamp)

    return (int(team), int.from_bytes(service, 'big'), payload, timestamp)


def _gen_mac(secret, protected_data):

    # Keccak does not need an HMAC construction, the secret can simply be prepended
    sha3 = hashlib.sha3_256()
    sha3.update(secret)
    sha3.update(protected_data)
    return sha3.digest()[:MAC_LEN]


class FlagVerificationError(Exception):
    """
    Base class for all Flag Exceptions.
    """


class InvalidFlagFormat(FlagVerificationError):
    """
    Flag does not match the expected format.
    """


class InvalidFlagMAC(FlagVerificationError):
    """
    MAC does not match with configured secret.
    """


class FlagExpired(FlagVerificationError):
    """
    Flag is already expired.
    """
