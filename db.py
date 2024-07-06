import sqlite3
from datetime import datetime

con = sqlite3.connect("server.db")

current_time = datetime.now().strftime('%H:%M:%S')
print(f'[{current_time}] Connection to the database successful')

cur = con.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS server (port,image,uuid,status)")
cur.close()
con.close()
def runsqlaction(action, params=()):
    con = sqlite3.connect("server.db")
    cur = con.cursor()
    cur.execute(action, params)
    resulta = cur.fetchall() 
    cur.close()
    con.commit()
    con.close()
    return resulta
