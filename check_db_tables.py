import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
# Remove +psycopg2 if needed
if 'postgresql+psycopg2://' in url:
    url = url.replace('postgresql+psycopg2://', 'postgresql://')

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = cur.fetchall()
    print("Tables in public schema:")
    for t in tables:
        print(f"- {t[0]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
