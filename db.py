import sqlite3
con = sqlite3.connect("server.db")
print('[hh:mm:ss] Connection to the database successful')
cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS server (port,image,uuid,status)")
cur.close()
con.close()
def runsqlaction(action, params=()):
    con = sqlite3.connect("server.db")
    cur = con.cursor()
    cur.execute(action, params)
    resulta = cur.fetchall()  # Fetching all results from the executed action
    cur.close()
    con.commit()
    con.close()
    return resulta
