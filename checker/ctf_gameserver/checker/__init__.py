#!/usr/bin/python3

import os

if 'CHECKER_CONTEST' in os.environ:
    from .contest import ContestChecker as BaseChecker
else:
    from .local import LocalChecker as BaseChecker

from .constants import *
