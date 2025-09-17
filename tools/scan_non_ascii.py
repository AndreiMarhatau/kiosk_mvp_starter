import sys
from pathlib import Path

def scan_file(path: Path):
    txt = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    bad = []
    for i, line in enumerate(txt, 1):
        if any(ord(ch) > 127 for ch in line):
            bad.append((i, line))
    return bad

def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('kiosk_app/main.py')
    bad = scan_file(target)
    for ln, line in bad:
        try:
            print(f"{ln}")
        except Exception:
            print(str(ln))

if __name__ == '__main__':
    main()
