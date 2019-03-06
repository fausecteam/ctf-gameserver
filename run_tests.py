#!/usr/bin/env python3

import unittest


def all_the_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.discover('submission', top_level_dir='submission'))
    suite.addTest(loader.discover('lib', top_level_dir='lib'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(all_the_tests())
