import sqlite3

connection = sqlite3.connect('database.db')

with open('dbschema.sql') as file:
    connection.executescript(file.read())

connection.commit()
connection.close()