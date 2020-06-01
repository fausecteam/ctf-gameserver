import base64
import binascii
import codecs
import struct
import time
import zlib

from .Keccak import Keccak

# Length of the MAC (in bits)
MAC_LEN = 80
# Length of the payload (in bytes)
PAYLOAD_LEN = 8
# timestamp + team + service + payload
DATA_LEN = 4 + 1 + 1 + PAYLOAD_LEN
# Flag prefix
PREFIX = "FAUST"
# Flag validity in seconds
VALID = 900

keccak = Keccak(100)


def generate(team_id, service_id, secret, payload=None, timestamp=None):
    """
    Generates a flag for the given arguments. This is deterministic and should always return the same
    result for the same arguments (and the same time, if no timestamp is explicitly specified).

    Args:
        team_id: ID of the team protecting this flag
        service_id: ID of the service this flag belongs to
        payload: 8 bytes of data to store in the flag, defaults to zero-padded
                 CRC32(timestamp, team, service)
        timestamp: Timestamp at which the flag expires, defaults to 15 minutes in the future
    """

    if timestamp is None:
        timestamp = time.time() + VALID

    protected_data = struct.pack("!i c c", int(timestamp), bytes([team_id]), bytes([service_id]))

    if payload is None:
        payload = struct.pack("!I I", zlib.crc32(protected_data), 0)

    protected_data += payload

    # Keccak does not need an HMAC construction, the secret can simply be prepended
    protected_hex = codecs.encode(secret, 'hex') + codecs.encode(protected_data, 'hex')
    mac_hex = keccak.Keccak(((len(secret) + len(protected_data))*8, protected_hex.decode('ascii')),
                            n=MAC_LEN)
    mac = codecs.decode(mac_hex, 'hex')

    return PREFIX + '_' + base64.b64encode(protected_data + mac).decode('ascii')


def verify(flag, secret):
    """
    Verfies flag validity and returns data from the flag.
    Will raise an appropriate exception if verification fails.

    Returns:
        Data from the flag as a tuple of (team, service, payload, timestamp)
    """

    if not flag.startswith(PREFIX + '_'):
        raise InvalidFlagFormat()

    try:
        raw_flag = base64.b64decode(flag.split('_')[1])
    except binascii.Error:
        raise InvalidFlagFormat()

    protected_data, flag_mac = raw_flag[:DATA_LEN], raw_flag[DATA_LEN:]
    protected_hex = codecs.encode(secret, 'hex') + codecs.encode(protected_data, 'hex')
    mac_hex = keccak.Keccak(((len(secret) + len(protected_data))*8, protected_hex.decode('ascii')),
                            n=MAC_LEN)
    mac = codecs.decode(mac_hex, 'hex')

    if not mac == flag_mac:
        raise InvalidFlagMAC()

    timestamp, team, service = struct.unpack("!i c c", protected_data[:6])
    payload = protected_data[6:]
    if time.time() - timestamp > 0:
        raise FlagExpired(time.time() - timestamp)

    return (int.from_bytes(team, 'big'), int.from_bytes(service, 'big'), payload, timestamp)


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

    pass
