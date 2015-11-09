#!/usr/bin/python3

from abc import ABCMeta, abstractmethod

import logging

class AbstractChecker(metaclass=ABCMeta):
    """Base class for custom checker scripts

    Individual checkers should import `BaseChecker` which does the
    right thing in terms of backend depending on whether you test
    locally or the checker is run during the Contest. They must
    implement the place_flag and check_flag methods and may add
    individual __init__ code. You may override the run method but need
    to keep it morally the same

    ident used for store/retrieve are supposed to match
    [A-Za-z0-9_-]+. It must be uniq for every (service,target)
    """
    def __init__(self, tick, team, service, ip):
        self._team = team
        self._tick = tick
        self._service = service
        self._tickduration = 300
        self._lookback = 5

    @abstractmethod
    def check_flag(self, tick):
        "Check for the flag from tick on the tested team's server"
        pass

    @abstractmethod
    def place_flag(self):
        "Place flag on the tested team's server"
        pass

    @abstractmethod
    def store_yaml(self, ident, yaml):
        "yaml needs to be a object that can be dumped by yaml.dump"
        pass

    @abstractmethod
    def store_blob(self, ident, blob):
        pass

    @abstractmethod
    def retrieve_yaml(self, ident):
        "returns object as deserialized by yaml.load"
        pass

    @abstractmethod
    def retrieve_blob(self, ident):
        pass

    @abstractmethod
    def get_flag(self, tick, payload=None):
        "returns the flag for tick possibly including payload"
        pass

    def run(self):
        logging.debug("Placing flag")
        result = self.place_flag()
        if result != 0:
            return result

        oldesttick = max(self._tick - self._lookback, -1)
        for tick in range(self._tick, oldesttick, -1):
            logging.debug("Checking for flag of tick %d" % tick)
            result = self.check_flag(tick)
            if result != 0:
                return result

        return 0
