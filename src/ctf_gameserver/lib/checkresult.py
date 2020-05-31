import enum


class CheckResult(enum.Enum):
    """
    Maps possible Checker results to their integer values.
    These integers map directly to the database! (See also: "web/scoring/models.py")
    """

    OK = 0
    TIMEOUT = 1
    FAULTY = 2
    FLAG_NOT_FOUND = 3
    RECOVERING = 4

    def __str__(self):
        return self.name
