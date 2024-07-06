from .. import db
def test_db():
    print("ok")
    db.runsqlaction("SELECT * FROM server")