import sys

from .daemon import run_spy

run_spy(float(sys.argv[1]) if len(sys.argv) > 1 else 0.3)
