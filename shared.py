import sys
import os
import webbrowser
import time
import json
import csv
from functools import partial
from pathlib import Path
from datetime import datetime
import re
import base64
import binascii
from io import BytesIO, StringIO

# optional serial is handled in serial_thread module

# optional pdf generation
try:
    from reportlab.pdfgen import canvas as pdfcanvas
    REPORTLAB_AVAILABLE = True
except Exception:
    pdfcanvas = None
    REPORTLAB_AVAILABLE = False

# DB helper
try:
    from app.models.database import get_connection
except Exception:
    get_connection = None

# constants
MAX_WIDTH = 820
SETTINGS_FILE = Path(__file__).parent / "settings.json"
EXPORTS_DIR = Path(__file__).parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)
EXPORTS_SESSION = EXPORTS_DIR / "session"
EXPORTS_BD = EXPORTS_DIR / "bd"
EXPORTS_SESSION.mkdir(parents=True, exist_ok=True)
EXPORTS_BD.mkdir(parents=True, exist_ok=True)


def load_settings():
    defaults = {"theme": "light"}
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return defaults
            return {**defaults, **data}
    except Exception:
        return defaults
    return defaults


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("No se pudo guardar settings:", e)


def get_db_conn():
    if get_connection is None:
        return None
    try:
        return get_connection()
    except Exception as e:
        print("DB get_db_conn error:", e)
        return None


def get_or_create_user_id(username: str):
    conn = get_db_conn()
    if conn is None:
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id_usuario FROM usuarios WHERE usuario = %s", (username,))
        row = cursor.fetchone()
        if row:
            if isinstance(row, dict):
                return row.get("id_usuario")
            return row[0]
        cursor.execute("INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s)", (username, ""))
        try:
            conn.commit()
        except Exception:
            pass
        return cursor.lastrowid if hasattr(cursor, "lastrowid") else None
    except Exception as e:
        print("DB get_or_create_user_id error:", e)
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def db_save_event(user_id, tipo_evento, detalle, origen, valor):
    if user_id is None:
        return False
    conn = get_db_conn()
    if conn is None:
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO eventos (id_usuario, tipo_evento, detalle, origen, valor) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (user_id, tipo_evento, detalle, origen, valor))
        try:
            conn.commit()
        except Exception:
            pass
        return True
    except Exception as e:
        print("DB save_event error:", e)
        return False
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def db_save_export_file(user_id, formato, filename=None, content_bytes=None):
    if user_id is None:
        return False
    conn = get_db_conn()
    if conn is None:
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        if content_bytes is not None:
            try:
                b64 = base64.b64encode(content_bytes).decode('ascii')
            except Exception:
                try:
                    b64 = base64.b64encode(str(content_bytes).encode('utf-8')).decode('ascii')
                except Exception:
                    b64 = None

            if b64:
                inserted = False
                try:
                    cursor.execute("INSERT INTO historialexportado (id_usuario, formato, contenido) VALUES (%s, %s, %s)",
                                   (user_id, formato, b64))
                    try:
                        conn.commit()
                    except Exception:
                        pass
                    inserted = True
                except Exception as e:
                    try:
                        msg = str(e).lower()
                        if 'unknown column' in msg or 'columna' in msg or 'contenido' in msg:
                            try:
                                cursor.execute("ALTER TABLE historialexportado ADD COLUMN contenido LONGBLOB")
                                try:
                                    conn.commit()
                                except Exception:
                                    pass
                                cursor.execute("INSERT INTO historialexportado (id_usuario, formato, contenido) VALUES (%s, %s, %s)",
                                               (user_id, formato, b64))
                                try:
                                    conn.commit()
                                except Exception:
                                    pass
                                inserted = True
                            except Exception:
                                inserted = False
                        else:
                            inserted = False
                    except Exception:
                        inserted = False

                if not inserted:
                    try:
                        cursor.execute("INSERT INTO historialexportado (id_usuario, formato, detalle) VALUES (%s, %s, %s)",
                                       (user_id, formato, b64))
                        try:
                            conn.commit()
                        except Exception:
                            pass
                        inserted = True
                    except Exception:
                        try:
                            cursor.execute("INSERT INTO historialexportado (id_usuario, formato, valor) VALUES (%s, %s, %s)",
                                           (user_id, formato, b64))
                            try:
                                conn.commit()
                            except Exception:
                                pass
                            inserted = True
                        except Exception:
                            inserted = False

                if inserted:
                    return True

        if filename:
            try:
                cursor.execute(
                    "INSERT INTO historialexportado (id_usuario, formato, filename) VALUES (%s, %s, %s)",
                    (user_id, formato, filename)
                )
                try:
                    conn.commit()
                except Exception:
                    pass
                return True
            except Exception:
                try:
                    cursor.execute("INSERT INTO historialexportado (id_usuario, formato, detalle) VALUES (%s, %s, %s)",
                                   (user_id, formato, filename))
                    try:
                        conn.commit()
                    except Exception:
                        pass
                    return True
                except Exception:
                    try:
                        cursor.execute("INSERT INTO historialexportado (id_usuario, formato) VALUES (%s, %s)", (user_id, formato))
                        try:
                            conn.commit()
                        except Exception:
                            pass
                        return True
                    except Exception:
                        return False

        try:
            cursor.execute("INSERT INTO historialexportado (id_usuario, formato) VALUES (%s, %s)", (user_id, formato))
            try:
                conn.commit()
            except Exception:
                pass
            return True
        except Exception as e:
            print("DB save_export_file error:", e)
            return False
    except Exception as e:
        print("DB save_export_file error:", e)
        return False
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def _extract_filename_from_row(cursor, row):
    candidates = ["filename", "file", "nombre", "ruta", "path", "detalle", "valor", "name"]
    try:
        if isinstance(row, dict):
            for c in candidates:
                if c in row and row[c]:
                    return str(row[c])
            for k, v in row.items():
                try:
                    if isinstance(v, str) and (v.lower().endswith(".pdf") or v.lower().endswith(".csv")):
                        return v
                except Exception:
                    pass
            return None
        desc = []
        try:
            desc = [d[0].lower() for d in cursor.description] if cursor and cursor.description else []
        except Exception:
            desc = []
        for idx, colname in enumerate(desc):
            if colname in candidates:
                try:
                    val = row[idx]
                    if val:
                        return str(val)
                except Exception:
                    pass
        for item in row:
            try:
                if isinstance(item, str) and (item.lower().endswith(".pdf") or item.lower().endswith(".csv")):
                    return item
            except Exception:
                pass
        return None
    except Exception:
        return None


def db_list_exported(formato=None):
    conn = get_db_conn()
    if conn is None:
        return []
    cursor = None
    out = []
    try:
        cursor = conn.cursor()
        if formato in ("CSV", "PDF"):
            cursor.execute("SELECT * FROM historialexportado WHERE formato=%s", (formato,))
        else:
            cursor.execute("SELECT * FROM historialexportado")
        rows = cursor.fetchall()
        if not rows:
            return []
        for r in rows:
            fn = _extract_filename_from_row(cursor, r)
            rec_id = None
            fecha = None
            fmt = None
            try:
                if isinstance(r, dict):
                    rec_id = r.get("id") or r.get("id_exportacion") or r.get("id_historial") or None
                    fecha = r.get("fecha_hora") or r.get("fecha_exportacion") or r.get("created_at") or None
                    fmt = r.get("formato")
                else:
                    desc_names = [d[0].lower() for d in cursor.description] if cursor.description else []
                    if "id" in desc_names:
                        rec_id = r[desc_names.index("id")]
                    elif "id_exportacion" in desc_names:
                        rec_id = r[desc_names.index("id_exportacion")]
                    if "fecha_hora" in desc_names:
                        fecha = r[desc_names.index("fecha_hora")]
                    elif "fecha_exportacion" in desc_names:
                        fecha = r[desc_names.index("fecha_exportacion")]
                    elif "created_at" in desc_names:
                        fecha = r[desc_names.index("created_at")]
                    if "formato" in desc_names:
                        fmt = r[desc_names.index("formato")]
            except Exception:
                pass
            out.append((rec_id, (fmt or "?"), fn, fecha))
        try:
            out_sorted = sorted(out, key=lambda x: x[3] or "", reverse=True)
        except Exception:
            out_sorted = out
        return out_sorted
    except Exception as e:
        print("db_list_exported error:", e)
        return []
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


def db_fetch_export_file(rec_id):
    conn = get_db_conn()
    if conn is None:
        return None
    cursor = None
    try:
        cursor = conn.cursor()
        for id_col in ("id_exportacion", "id", "id_historial"):
            try:
                cursor.execute(f"SELECT * FROM historialexportado WHERE {id_col}=%s LIMIT 1", (rec_id,))
                rows = cursor.fetchall()
                if not rows:
                    continue
                row = rows[0]
                row_map = {}
                if isinstance(row, dict):
                    row_map = row
                else:
                    try:
                        desc = [d[0].lower() for d in cursor.description] if cursor.description else []
                        for idx, name in enumerate(desc):
                            try:
                                row_map[name] = row[idx]
                            except Exception:
                                pass
                    except Exception:
                        pass

                def _try_decode_b64_from_text(text):
                    s_clean = re.sub(r"\s+", "", text)
                    try:
                        decoded = base64.b64decode(s_clean, validate=False)
                        return decoded
                    except Exception:
                        return None

                def _is_likely_pdf(bts):
                    return bts[:4] == b"%PDF"

                def _is_likely_text_csv(bts):
                    try:
                        txt = bts.decode('utf-8', errors='ignore')
                        return (',' in txt) and ('\n' in txt or '\r' in txt)
                    except Exception:
                        return False

                if 'contenido' in row_map and row_map.get('contenido'):
                    val = row_map['contenido']
                    if isinstance(val, (bytes, bytearray)):
                        b = bytes(val)
                        if _is_likely_pdf(b) or not all(32 <= x <= 127 or x in (9,10,13) for x in b[:64]):
                            return b
                        try:
                            txt = b.decode('utf-8', errors='ignore')
                            decoded = _try_decode_b64_from_text(txt)
                            if decoded:
                                if _is_likely_pdf(decoded) or _is_likely_text_csv(decoded):
                                    return decoded
                                try:
                                    _ = decoded.decode('utf-8')
                                    return decoded
                                except Exception:
                                    return b
                            else:
                                return b
                        except Exception:
                            return b
                    elif isinstance(val, str):
                        s = val.strip()
                        if s.lower().endswith('.pdf') or s.lower().endswith('.csv'):
                            return None
                        decoded = _try_decode_b64_from_text(s)
                        if decoded:
                            return decoded
                        else:
                            return s.encode('utf-8')

                candidates = ["file", "data", "blob", "detalle", "valor", "contenido_base64", "content", "archivo", "filename"]
                for c in candidates:
                    if c in row_map and row_map[c]:
                        val = row_map[c]
                        if isinstance(val, (bytes, bytearray)):
                            return bytes(val)
                        if isinstance(val, str):
                            s = val.strip()
                            if s.lower().endswith('.pdf') or s.lower().endswith('.csv'):
                                continue
                            decoded = _try_decode_b64_from_text(s)
                            if decoded:
                                return decoded
                            else:
                                return s.encode('utf-8')
                return None
            except Exception:
                continue
        return None
    except Exception as e:
        print("db_fetch_export_file error:", e)
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass
