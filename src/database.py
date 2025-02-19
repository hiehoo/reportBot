import sqlite3
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='reports.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.setup_tables()

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

    def setup_tables(self):
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                group_name TEXT,
                topic_id INTEGER DEFAULT 0,
                added_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                user_id INTEGER,
                username TEXT,
                report_date DATE,
                report_content TEXT,
                submitted_at TIMESTAMP,
                chat_id INTEGER,
                topic_id INTEGER DEFAULT 0
            );
        ''')
        self.conn.commit()

    def add_group(self, chat_id, group_name, topic_id=0, timezone='Asia/Bangkok'):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO groups (chat_id, group_name, topic_id, added_at)
                VALUES (?, ?, ?, ?)
            ''', (chat_id, group_name, topic_id, datetime.now(pytz.timezone(timezone))))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding group: {str(e)}")
            self.conn.rollback()

    def add_report(self, user_id, username, report_content, chat_id, timezone='Asia/Bangkok'):
        try:
            tz = pytz.timezone(timezone)
            current_date = datetime.now(tz).date()
            self.cursor.execute('''
                INSERT INTO reports (user_id, username, report_date, report_content, submitted_at, chat_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, current_date, report_content, datetime.now(tz), chat_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding report: {str(e)}")
            self.conn.rollback()
            return False

    def get_reported_users(self, chat_id, date):
        try:
            self.cursor.execute('''
                SELECT username FROM reports 
                WHERE date(report_date) = date(?)
                AND chat_id = ?
            ''', (date, chat_id))
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting reported users: {str(e)}")
            return []

    def get_all_groups(self):
        try:
            self.cursor.execute('SELECT chat_id FROM groups')
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting groups: {str(e)}")
            return [] 