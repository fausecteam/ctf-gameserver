#!/usr/bin/python3

from .local import LocalChecker as BaseChecker
#from .contest import ContestChecker as BaseChecker

OK = 0
TIMEOUT = 1
NOTWORKING = 2
NOTFOUND = 3

_mapping = ["OK", "TIMEOUT", "NOTWORKING", "NOTFOUND"]

def string_to_result(strresult):
    return _mapping.index(strresult)

def result_to_string(result):
    return _mapping[result]
