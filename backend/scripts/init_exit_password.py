import os, sqlite3

DB = os.path.join('app','kiosk.db')
con = sqlite3.connect(DB)
cur = con.cursor()

# ensure settings table exists (minimal bootstrap)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
exists = cur.fetchone() is not None
if not exists:
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS themes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, primary TEXT, bg TEXT, text TEXT, logo_path TEXT
    );
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_name TEXT, footer_qr_text TEXT, footer_clock_format TEXT,
        theme_id INTEGER, exit_password_hash TEXT
    );
    ''')

# ensure column exit_password_hash
cols = {r[1] for r in cur.execute("PRAGMA table_info(settings)").fetchall()}
if 'exit_password_hash' not in cols:
    cur.execute("ALTER TABLE settings ADD COLUMN exit_password_hash TEXT")

# ensure single settings row
row = cur.execute("SELECT id, theme_id FROM settings LIMIT 1").fetchone()
if not row:
    cur.execute("INSERT INTO themes(name, primary, bg, text, logo_path) VALUES(?,?,?,?,?)",
                ('default','#2563eb','#f5f7fb','#0f1419',None))
    theme_id = cur.lastrowid
    cur.execute("INSERT INTO settings(org_name, footer_qr_text, footer_clock_format, theme_id, exit_password_hash) VALUES(?,?,?,?,?)",
                ('Организация','', '%H:%M', theme_id, None))

con.commit(); con.close()
print('DB initialized')
