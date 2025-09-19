from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QPlainTextEdit
from pathlib import Path
import csv
import os
import webbrowser
from datetime import datetime
from io import BytesIO, StringIO
import base64
import shutil

from app.utils.shared import (
    EXPORTS_SESSION,
    EXPORTS_BD,
    db_list_exported,
    db_fetch_export_file,
    db_save_export_file,
    REPORTLAB_AVAILABLE,
    pdfcanvas,
)
from app.utils.shared import get_db_conn


def export_dialog(parent):
    try:
        default = str(Path.home() / f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv")
        path, _ = QFileDialog.getSaveFileName(parent, "Guardar exportación", default, "CSV (*.csv);;PDF (*.pdf)")
        if not path:
            return None
        if path.lower().endswith('.csv'):
            return export_session(parent, format='csv', filename=Path(path))
        else:
            return export_session(parent, format='pdf', filename=Path(path))
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"No se pudo abrir dialogo de exportación: {e}")
        return None


def _make_csv_bytes(history):
    # csv.writer expects a text file; use StringIO and then encode to bytes
    buf = StringIO()
    try:
        writer = csv.writer(buf)
        writer.writerow(['timestamp', 'led', 'event'])
        for r in history or []:
            writer.writerow(r)
        return buf.getvalue().encode('utf-8')
    finally:
        try:
            buf.close()
        except Exception:
            pass


def _make_pdf_bytes(history):
    # Very small PDF generator using reportlab if available
    buf = BytesIO()
    try:
        if not REPORTLAB_AVAILABLE or pdfcanvas is None:
            return None
        from reportlab.lib.pagesizes import A4
        c = pdfcanvas.Canvas(buf, pagesize=A4)
        w, h = A4
        y = h - 40
        c.setFont('Helvetica', 12)
        c.drawString(40, y, 'Historial de sesión')
        y -= 24
        c.setFont('Helvetica', 9)
        for r in history or []:
            line = f"{r[0]} | LED:{r[1]} | {r[2]}"
            # wrap if necessary
            if y < 60:
                c.showPage()
                y = h - 40
                c.setFont('Helvetica', 9)
            c.drawString(40, y, line[:200])
            y -= 14
        c.save()
        data = buf.getvalue()
        return data
    except Exception:
        return None
    finally:
        try:
            buf.close()
        except Exception:
            pass


def export_session(parent, format="csv", filename: Path = None):
    try:
        ts_fn = getattr(parent, '_safe_timestamp_str', None)
        if callable(ts_fn):
            ts = ts_fn()
        else:
            ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    # Do not create EXPORTS_SESSION automatically; if no filename provided, ask user where to save

        hist = getattr(parent, 'history', []) or []

        if format == 'csv':
            if not filename:
                # ask where to save
                default = str(Path.home() / f"session_{ts}.csv")
                path, _ = QFileDialog.getSaveFileName(parent, "Guardar exportación (CSV)", default, "CSV (*.csv)")
                if not path:
                    return None
                filename = Path(path)
            else:
                filename = Path(filename)
            # create CSV bytes and save
            data_bytes = _make_csv_bytes(hist)
            with open(filename, 'wb') as f:
                f.write(data_bytes)
                # Do not create global EXPORTS_BD automatically; the user chose `filename` so keep only that.
            # try to store in DB if user id exists
            try:
                uid = getattr(parent, 'db_user_id', None)
                if uid:
                    db_save_export_file(uid, 'CSV', filename=str(filename), content_bytes=data_bytes)
            except Exception:
                pass
            QMessageBox.information(parent, "Exportado", f"CSV guardado en: {filename}")
            return filename

        elif format == 'pdf':
            # generate PDF bytes
            data_bytes = _make_pdf_bytes(hist)
            if data_bytes is None:
                QMessageBox.information(parent, "Exportar PDF", "ReportLab no está disponible; no se puede generar PDF.")
                return None
            if not filename:
                default = str(Path.home() / f"session_{ts}.pdf")
                path, _ = QFileDialog.getSaveFileName(parent, "Guardar exportación (PDF)", default, "PDF (*.pdf)")
                if not path:
                    return None
                filename = Path(path)
            else:
                filename = Path(filename)
            with open(filename, 'wb') as f:
                f.write(data_bytes)
                # Do not create global EXPORTS_BD automatically; the user chose `filename` so keep only that.
            try:
                uid = getattr(parent, 'db_user_id', None)
                if uid:
                    db_save_export_file(uid, 'PDF', filename=str(filename), content_bytes=data_bytes)
            except Exception:
                pass
            QMessageBox.information(parent, "Exportado", f"PDF guardado en: {filename}")
            return filename

        else:
            QMessageBox.information(parent, "Exportar", "Formato no soportado.")
            return None
    except Exception as e:
        QMessageBox.critical(parent, "Error exportando", str(e))
        return None


def show_csv_table(parent, csv_path: Path):
    try:
        if csv_path and Path(csv_path).exists():
            webbrowser.open(str(csv_path))
        else:
            QMessageBox.information(parent, "Abrir CSV", "El archivo CSV no existe.")
    except Exception as e:
        QMessageBox.information(parent, "Abrir CSV", f"Error al abrir CSV: {e}")


def view_exports_dialog(parent):
    try:
        rows = db_list_exported()
        # If DB not available, inform user and fallback to filesystem listing
        if get_db_conn() is None:
            QMessageBox.information(parent, 'Exportados', 'No es posible conectar a la base de datos. Se listarán archivos en disco si existen.')

        # If DB returned nothing, try filesystem fallback: list files under EXPORTS_BD
        fs_mode = False
        if not rows:
            try:
                files = []
                if EXPORTS_BD.exists() and EXPORTS_BD.is_dir():
                    for p in sorted(EXPORTS_BD.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                        if p.is_file():
                            fmt = p.suffix.lstrip('.').upper() if p.suffix else ''
                            # Use a synthetic id starting with FS: so we can detect it later
                            rec_id = f"FS:{str(p)}"
                            fecha = datetime.fromtimestamp(p.stat().st_mtime)
                            files.append((rec_id, (fmt or '?'), p.name, fecha))
                if files:
                    rows = files
                    fs_mode = True
                else:
                    QMessageBox.information(parent, "Exportados", "No hay archivos exportados registrados en BD.")
                    return
            except Exception:
                QMessageBox.information(parent, "Exportados", "No hay archivos exportados registrados en BD.")
                return

        dlg = QDialog(parent)
        dlg.setWindowTitle('Exportados (BD)')
        layout = QVBoxLayout(dlg)
        info = QLabel(f'Se encontraron {len(rows)} registros. Selecciona uno para abrir:')
        layout.addWidget(info)
        lw = QListWidget()
        id_map = {}
        for rec in rows:
            rec_id, fmt, fn, fecha = rec
            display = f"{rec_id} | {fmt or '?'} | {fn or 'sin_nombre'} | {fecha or ''}"
            item = display
            lw.addItem(item)
            id_map[item] = rec_id
        layout.addWidget(lw)

        buttons_h = QHBoxLayout()
        btn_open = QPushButton('Abrir')
        btn_cancel = QPushButton('Cancelar')
        buttons_h.addStretch()
        buttons_h.addWidget(btn_open)
        buttons_h.addWidget(btn_cancel)
        layout.addLayout(buttons_h)

        def on_open():
            sel = lw.currentItem()
            if not sel:
                QMessageBox.information(dlg, 'Seleccionar', 'Por favor selecciona un registro.')
                return
            rec_id = id_map.get(sel.text())
            # If this is a filesystem fallback entry, open the file directly
            if isinstance(rec_id, str) and rec_id.startswith('FS:'):
                fp = rec_id[3:]
                try:
                    if Path(fp).exists():
                        webbrowser.open(str(fp))
                        dlg.accept()
                        return
                    else:
                        QMessageBox.information(dlg, 'Exportado', 'El archivo ya no existe en disco.')
                        return
                except Exception as e:
                    QMessageBox.information(dlg, 'Exportado', f'No se pudo abrir el archivo: {e}')
                    return

            data = db_fetch_export_file(rec_id)
            if not data:
                QMessageBox.information(dlg, 'Exportado', 'No se pudo obtener contenido del registro.')
                return

            # If bytes, try detect PDF vs CSV. If str, treat as CSV text.
            is_bytes = isinstance(data, (bytes, bytearray))
            try:
                if is_bytes:
                    # detect PDF
                    if data[:4] == b'%PDF':
                        # Write to a system temp file and open with default PDF viewer
                        import tempfile, os as _os
                        try:
                            tf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                            tf.write(data)
                            tf.flush()
                            tf.close()
                            # On Windows use os.startfile, otherwise fallback to webbrowser
                            try:
                                _os.startfile(tf.name)
                            except Exception:
                                webbrowser.open(f'file://{tf.name}')
                            dlg.accept()
                            return
                        except Exception as e:
                            QMessageBox.information(dlg, 'Exportado', f'No se pudo abrir PDF temporal: {e}')
                            return
                    else:
                        # attempt decode as text and show in dialog
                        try:
                            txt = data.decode('utf-8')
                        except Exception:
                            txt = data.decode('latin-1', errors='ignore')
                        show_dlg = QDialog(parent)
                        show_dlg.setWindowTitle('Exportado (vista)')
                        v = QVBoxLayout(show_dlg)
                        te = QPlainTextEdit()
                        te.setReadOnly(True)
                        te.setPlainText(txt)
                        v.addWidget(te)
                        btn = QPushButton('Cerrar')
                        btn.clicked.connect(show_dlg.accept)
                        v.addWidget(btn)
                        show_dlg.exec()
                        return
                else:
                    # string-like: show as CSV text
                    txt = str(data)
                    show_dlg = QDialog(parent)
                    show_dlg.setWindowTitle('Exportado (vista)')
                    v = QVBoxLayout(show_dlg)
                    te = QPlainTextEdit()
                    te.setReadOnly(True)
                    te.setPlainText(txt)
                    v.addWidget(te)
                    btn = QPushButton('Cerrar')
                    btn.clicked.connect(show_dlg.accept)
                    v.addWidget(btn)
                    show_dlg.exec()
                    return
            except Exception as e:
                QMessageBox.information(dlg, 'Exportado', f'No se pudo mostrar el contenido en memoria: {e}')
                return

        btn_open.clicked.connect(on_open)
        btn_cancel.clicked.connect(dlg.reject)

        dlg.exec()
    except Exception as e:
        QMessageBox.information(parent, "Ver exportados", f"Error: {e}")
