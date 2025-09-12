import sqlite3
import os

def main():
    path = os.path.join('app','kiosk.db')
    con = sqlite3.connect(path)
    cur = con.cursor()
    for t in ['settings','themes','buttons','pages','blocks','users']:
        try:
            cur.execute(f'PRAGMA table_info({t})')
            cols = cur.fetchall()
            print('TABLE', t)
            for c in cols:
                print('  -', c[1], c[2])
        except Exception as e:
            print('TABLE', t, 'ERROR', e)
    print('--- sample rows: settings, themes')
    for t in ['settings','themes']:
        try:
            cur.execute(f'SELECT * FROM {t} LIMIT 3')
            for r in cur.fetchall():
                print(t, r)
        except Exception as e:
            print('read error', t, e)
    con.close()

if __name__ == '__main__':
    main()

