import sqlite3
from werkzeug.security import generate_password_hash

connection = sqlite3.connect('SQLite.db', check_same_thread=False)
cursor = connection.cursor()

cursor.execute('CREATE TABLE comments ( id INTEGER PRIMARY KEY, author_id INTEGER NOT NULL, post_id INTEGER NOT NULL, text TEXT NOT NULL )')

connection.commit()
connection.close()

pythonaware_username = ziqprd
pytohnaware_password = q#Xm5we,?/f2G#K