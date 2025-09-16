import pymysql
from pymysql.err import MySQLError
from app.utils.config import DB_CONFIG

def get_connection():
    """Devuelve una conexión PyMySQL o None (y muestra el error en stdout)."""
    try:
        conn = pymysql.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            port=DB_CONFIG["port"],
            connect_timeout=3,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return conn
    except MySQLError as e:
        return None

class Database:
    """Clase auxiliar si quieres usar objetos."""
    def __init__(self):
        self.connection = None
        self.last_error = None

    def connect(self):
        try:
            self.connection = get_connection()
            return self.connection is not None
        except MySQLError as e:
            self.last_error = e
            return False

    def close(self):
        try:
            if self.connection:
                self.connection.close()
        except Exception as e:
            pass
