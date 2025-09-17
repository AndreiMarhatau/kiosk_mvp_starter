from pathlib import Path

p = Path('kiosk_app/main.py')
lines = p.read_text(encoding='utf-8', errors='surrogatepass').splitlines()
for i, line in enumerate(lines):
    if 'setWindowTitle(' in line:
        lines[i] = '        self.setWindowTitle("Kiosk")'
p.write_text('\n'.join(lines), encoding='utf-8')
print('fixed titles')
