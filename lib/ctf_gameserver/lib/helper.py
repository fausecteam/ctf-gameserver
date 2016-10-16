#!/usr/bin/python3
# -*- coding: utf-8 -*-

def convert_arg_line_to_args(arg_line):
    if arg_line.strip().startswith('#'):
        return []
    else:
        return arg_line.split()
