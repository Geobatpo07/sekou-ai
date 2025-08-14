import os
import sys

# Ensure project root is on sys.path when running tests in environments
# where the current working directory may not be added automatically.
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
