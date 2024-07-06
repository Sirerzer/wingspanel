import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import yml  # Now it should find yml.py in the parent directory

def test_yml():
    var = yml.test_yml()
    print(vars(var))