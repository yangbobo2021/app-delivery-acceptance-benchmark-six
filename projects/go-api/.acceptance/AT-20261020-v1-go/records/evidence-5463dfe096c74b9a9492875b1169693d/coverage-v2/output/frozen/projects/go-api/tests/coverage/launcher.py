#!/opt/homebrew/bin/python3
"""Subprocess entry: application flags remain untouched after the test separator."""
import os
import sys
binary = os.environ['ACCEPTANCE_COVERAGE_TEST_BINARY']
raw = os.environ['ACCEPTANCE_COVERAGE_RAW']
os.execv(binary, [binary, '-test.run=^TestCoverageProcess$', '-test.gocoverdir='+raw, '--', *sys.argv[1:]])
