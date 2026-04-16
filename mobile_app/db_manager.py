import sqlite3
import os

class DBManager:
    """
    Handles local persistence (SQLite) within the mobile_app directory structure.
    Stores historical alerts and reference paths to visual proof locally.
    """
    def __init__(self, db_filename='nri_alerts.db'):
        # On Android, Kivy requires the db to reside in the app's private files directory.
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                context = PythonActivity.getActiveSheet()
                dir_path = context.getFilesDir().getAbsolutePath()
                self.db_path = os.path.join(dir_path, db_filename)
            except Exception as e:
                print(f"Fallback DB Path. JNIUS Error: {e}")
                self.db_path = db_filename
        else:
            self.db_path = db_filename
            
        self.init_schema()

    def init_schema(self):
        """Creates the 'alerts' table mapping to the Sentinel alert structure."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                level TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                image_path TEXT,
                raw_payload TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def save_alert(self, alert_id, alert_type, level, timestamp, image_path, raw_payload):
        """Inserts incoming alerts ensuring they persist after an app restart."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO alerts (id, type, level, timestamp, image_path, raw_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_id, alert_type, level, timestamp, image_path, raw_payload))
            conn.commit()
        except sqlite3.Error as e:
            print(f"DB Insert error: {e}")
        finally:
            conn.close()
