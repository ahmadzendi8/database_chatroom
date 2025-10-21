import requests
import psycopg2
import time
import os
import json
from datetime import datetime, timezone, timedelta

# --- PostgreSQL Connection ---
PGHOST = os.environ.get("PGHOST", "")
PGPORT = os.environ.get("PGPORT", "")
PGUSER = os.environ.get("PGUSER", "")
PGPASSWORD = os.environ.get("PGPASSWORD", "")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "")

conn = psycopg2.connect(
    dbname=POSTGRES_DB,
    user=PGUSER,
    password=PGPASSWORD,
    host=PGHOST,
    port=PGPORT
)
c = conn.cursor()
# Tabel request
c.execute("""
CREATE TABLE IF NOT EXISTS request (
    id SERIAL PRIMARY KEY,
    data JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);
""")
# Tabel chat
c.execute('''
CREATE TABLE IF NOT EXISTS chat (
    id BIGINT PRIMARY KEY,
    username TEXT,
    content TEXT,
    timestamp BIGINT,
    timestamp_wib TEXT,
    level INT DEFAULT 0
)
''')
conn.commit()

WIB = timezone(timedelta(hours=7))
url = "https://indodax.com/api/v2/chatroom/history"

def polling_chat():
    seen_ids = set()
    print("Polling chat Indodax aktif... (Ctrl+C untuk berhenti)")
    while True:
        try:
            response = requests.get(url)
            data = response.json()
            if data.get("success"):
                chat_list = data["data"]["content"]
                new_chats = []
                for chat in chat_list:
                    if chat['id'] not in seen_ids:
                        seen_ids.add(chat['id'])
                        chat_time_utc = datetime.fromtimestamp(chat["timestamp"], tz=timezone.utc)
                        chat_time_wib = chat_time_utc.astimezone(WIB)
                        chat["timestamp_wib"] = chat_time_wib.strftime('%Y-%m-%d %H:%M:%S')
                        chat["level"] = int(chat.get("level", 0))
                        new_chats.append(chat)
                if new_chats:
                    for chat in new_chats:
                        try:
                            c.execute('''
                                INSERT INTO chat (id, username, content, timestamp, timestamp_wib, level)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id) DO NOTHING
                            ''', (chat['id'], chat['username'], chat['content'], chat['timestamp'], chat['timestamp_wib'], chat['level']))
                        except Exception as e:
                            print(f"Error insert chat: {e} | Data: {chat}")
                            conn.rollback()
                    conn.commit()
                    print(f"{len(new_chats)} chat baru disimpan ke database.")
                else:
                    print("Tidak ada chat baru.")
            else:
                print("Gagal mengambil data dari API.")
        except Exception as e:
            print(f"Error polling chat: {e}")
            conn.rollback()
        time.sleep(1)

if __name__ == "__main__":
    polling_chat()
