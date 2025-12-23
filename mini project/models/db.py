# models/db.py
import pymysql

def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        db=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False  # we'll control transactions
    )

