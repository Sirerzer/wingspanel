import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import db  # Now it should find db.py in the parent directory

def test_db():
    print("ok")
    db.runsqlaction("SELECT * FROM server")