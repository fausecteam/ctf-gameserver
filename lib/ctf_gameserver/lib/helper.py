# -*- coding: utf-8 -*-

import shlex

def convert_arg_line_to_args(arg_line):
    """argparse helper for splitting input from config

    Allows comment lines in configfiles and allows both argument and
    value on the same line
    """
    return shlex.split(arg_line, comments=True)
