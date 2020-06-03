import enum


class CheckResult(enum.Enum):
    """
    Maps possible Checker results to their integer values.
    These integers map directly to the database! (See also: "web/scoring/models.py")
    """

    OK = 0
    DOWN = 1      # Error in the network connection, e.g. a timeout or connection abort
    FAULTY = 2    # Service is available, but not behaving as expected
    FLAG_NOT_FOUND = 3
    RECOVERING = 4

    def __str__(self):
        return self.name
