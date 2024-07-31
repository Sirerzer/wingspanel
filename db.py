import sqlite3
from datetime import datetime

def print_current_time():
    return datetime.now().strftime('%H:%M:%S')

def connect_db():
    return sqlite3.connect("server.db")

def setup_db():
    con = connect_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS server (
            port TEXT,
            image TEXT,
            uuid TEXT PRIMARY KEY,
            dockeruuid TEXT,
            status TEXT,
            ndd TEXT
        )
    """)
    con.commit()
    cur.close()
    con.close()

def runsqlaction(action, params=()):
    con = connect_db()
    cur = con.cursor()
    try:
        cur.execute(action, params)
        resulta = cur.fetchall()
        con.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        resulta = []
    finally:
        cur.close()
        con.close()
    return resulta

def get_docker_uuid(uuid):
    if uuid is None:
        print(f"[{print_current_time()}] Error: UUID is None")
        return None

    action = "SELECT dockeruuid FROM server WHERE uuid = ?"
    result = runsqlaction(action, (uuid,))
    if result:
        return result[0][0]
    else:
        print(f"[{print_current_time()}] Error: UUID {uuid} not found in the database")
    return None

# Setup the database
setup_db()

# Example usage
