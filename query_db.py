import psycopg2

conn = psycopg2.connect("postgresql://postgres.qhckollxjxoxmvqrjdpy:zTdsz9jp%26X%40BHsn@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres")
cur = conn.cursor()
cur.execute("SELECT id, email, password_hash, is_active FROM users")
for row in cur.fetchall():
    print(row)
