from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel
from pathlib import Path
import csv
import os
import webbrowser
from datetime import datetime
from io import BytesIO, StringIO

from app.utils.shared import (
    EXPORTS_SESSION,
    EXPORTS_BD,
    db_list_exported,
    db_fetch_export_file,
    db_save_export_file,
    REPORTLAB_AVAILABLE,
    pdfcanvas,
)


def export_dialog(parent):
    try:
        default = str(EXPORTS_SESSION / f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv")
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

        EXPORTS_SESSION.mkdir(parents=True, exist_ok=True)

        hist = getattr(parent, 'history', []) or []

        if format == 'csv':
            if not filename:
                filename = EXPORTS_SESSION / f"session_{ts}.csv"
            else:
                filename = Path(filename)
            # create CSV bytes and save
            data_bytes = _make_csv_bytes(hist)
            with open(filename, 'wb') as f:
                f.write(data_bytes)
            # try to store in DB if user id exists
            try:
                uid = getattr(parent, 'db_user_id', None)
                if uid:
                    db_save_export_file(uid, 'CSV', filename=str(filename), content_bytes=data_bytes)
            except Exception:
                pass
            QMessageBox.information(parent, "Exportado", f"CSV guardado en: {filename}")
            try:
                webbrowser.open(str(filename))
            except Exception:
                pass
            return filename

        elif format == 'pdf':
            # generate PDF bytes
            data_bytes = _make_pdf_bytes(hist)
            if data_bytes is None:
                QMessageBox.information(parent, "Exportar PDF", "ReportLab no está disponible; no se puede generar PDF.")
                return None
            if not filename:
                filename = EXPORTS_SESSION / f"session_{ts}.pdf"
            else:
                filename = Path(filename)
            with open(filename, 'wb') as f:
                f.write(data_bytes)
            try:
                uid = getattr(parent, 'db_user_id', None)
                if uid:
                    db_save_export_file(uid, 'PDF', filename=str(filename), content_bytes=data_bytes)
            except Exception:
                pass
            QMessageBox.information(parent, "Exportado", f"PDF guardado en: {filename}")
            try:
                webbrowser.open(str(filename))
            except Exception:
                pass
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
        if not rows:
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
            data = db_fetch_export_file(rec_id)
            if not data:
                QMessageBox.information(dlg, 'Exportado', 'No se pudo obtener contenido del registro.')
                return
            EXPORTS_BD.mkdir(parents=True, exist_ok=True)
            # find row info to determine extension/filename
            chosen = None
            for r in rows:
                if r[0] == rec_id:
                    chosen = r
                    break
            fmt = (chosen[1] or '').lower() if chosen else ''
            fn = chosen[2] if chosen and chosen[2] else f'export_{rec_id}.{fmt or "bin"}'
            outp = EXPORTS_BD / fn
            try:
                if isinstance(data, (bytes, bytearray)):
                    outp.write_bytes(data)
                else:
                    outp.write_text(str(data), encoding='utf-8')
            except Exception as e:
                QMessageBox.information(dlg, 'Guardar', f'No se pudo guardar archivo: {e}')
                return
            try:
                webbrowser.open(str(outp))
            except Exception:
                pass
            dlg.accept()

        btn_open.clicked.connect(on_open)
        btn_cancel.clicked.connect(dlg.reject)

        dlg.exec()
    except Exception as e:
        QMessageBox.information(parent, "Ver exportados", f"Error: {e}")
