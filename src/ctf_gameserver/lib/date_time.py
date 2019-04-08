import datetime


def ensure_utc_aware(datetime_or_time):
    """
    Ensures that a datetime or time object is timezone-aware.
    For naive objects, a new object is returned with its timezone set to UTC. Already timezone-aware objects
    are returned as-is, without any timezone change or conversion.
    """

    if datetime_or_time is None:
        return None

    # This is how timezone-awareness is officially defined
    if datetime_or_time.tzinfo is not None:
        if isinstance(datetime_or_time, datetime.datetime):
            if datetime_or_time.tzinfo.utcoffset(datetime_or_time) is not None:
                return datetime_or_time
        elif isinstance(datetime_or_time, datetime.time):
            if datetime_or_time.tzinfo.utcoffset(None) is not None:
                return datetime_or_time
        else:
            raise TypeError('ensure_utc_aware() can only handle datetime and time objects')

    return datetime_or_time.replace(tzinfo=datetime.timezone.utc)
