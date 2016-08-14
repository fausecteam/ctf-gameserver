#!/usr/bin/python3

OK = 0
TIMEOUT = 1
NOTWORKING = 2
NOTFOUND = 3
RECOVERING = 4

_mapping = ["OK", "TIMEOUT", "NOTWORKING", "NOTFOUND", "RECOVERING"]

def string_to_result(strresult):
    return _mapping.index(strresult)

def result_to_string(result):
    return _mapping[result]
