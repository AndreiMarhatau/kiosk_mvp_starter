from pathlib import Path

p = Path('kiosk_app/main.py')
text = p.read_text(encoding='utf-8', errors='surrogatepass')

lines = text.splitlines()
for i, line in enumerate(lines):
    if 'self.setWindowTitle' in line:
        # normalize the title to a clean constant
        lines[i] = '        self.setWindowTitle("Kiosk")'
        break

p.write_text("\n".join(lines), encoding='utf-8')
print('patched title')

