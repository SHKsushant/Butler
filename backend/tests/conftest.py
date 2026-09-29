import os
import sys

# Make `app.*` importable when running `pytest` from the backend/ directory
# or from anywhere else in the repo.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
