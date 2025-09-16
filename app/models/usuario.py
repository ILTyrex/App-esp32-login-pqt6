# app/models/usuario.py
from app.models.database import get_connection
from pymysql.err import MySQLError
from app.utils.auth_service import hash_password

class UsuarioModel:
    def __init__(self):
        pass

    def crear_usuario(self, usuario, contrasena):
        conn = get_connection()

        if not conn:
            return False, "No se pudo conectar a la base de datos."
        cursor = None
        try:
            cursor = conn.cursor()

            # 👇 Verificar si el usuario ya existe
            cursor.execute("SELECT id_usuario FROM usuarios WHERE usuario = %s", (usuario,))
            if cursor.fetchone():
                return False, "El usuario ya existe."

            # 👇 Si no existe, hacemos el hash y lo insertamos
            hashed_pwd = hash_password(contrasena)
            sql = "INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)"
            cursor.execute(sql, (usuario, hashed_pwd))
            conn.commit()
            return True, "Usuario registrado correctamente."

        except MySQLError as e:
            # Ya no debería saltar 1062 porque lo verificamos antes, pero lo dejamos por seguridad
            if getattr(e, "args", [None])[0] == 1062:
                return False, "El usuario ya existe."
            return False, f"Error MySQL: {e}"

        except Exception as e:
            return False, f"Error inesperado: {e}"

        finally:
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception:
                pass

    def obtener_usuario(self, usuario):
        conn = get_connection()
        if not conn:
            return None
        cursor = None
        try:
            cursor = conn.cursor()  # con DictCursor en get_connection ya devuelve dict
            sql = "SELECT * FROM usuarios WHERE usuario = %s"
            cursor.execute(sql, (usuario,))
            row = cursor.fetchone()
            return row
        except Exception as e:
            return None
        finally:
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception as e:
                pass
