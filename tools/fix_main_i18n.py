import re
from pathlib import Path

p = Path('kiosk_app/main.py')
text = p.read_text(encoding='utf-8', errors='ignore')

# Replace window title
text = re.sub(r"self\.setWindowTitle\([^\)]*\)", "self.setWindowTitle(t('password'))", text)

# Replace title QLabel
text = re.sub(r"title\s*=\s*QLabel\([^\)]*\)", "title = QLabel(t('exit_password'))", text)

# Replace QLineEdit placeholder
text = re.sub(r"self\.edit\s*=\s*QLineEdit\(\);\s*self\.edit\.setEchoMode\(QLineEdit\.Password\);\s*self\.edit\.setPlaceholderText\([^\)]*\)",
              "self.edit = QLineEdit(); self.edit.setEchoMode(QLineEdit.Password); self.edit.setPlaceholderText(t('password'))",
              text)

# Replace checkbox text
text = re.sub(r"self\.cb\s*=\s*QCheckBox\([^\)]*\)", "self.cb = QCheckBox(t('show_password'))", text)

# Home button text
text = re.sub(r"self\.home_btn\s*=\s*QPushButton\([^\)]*\)", "self.home_btn = QPushButton(t('home'))", text)

src = text

# Generic cleanup for garbled UI texts in common widgets where non-ascii appears
def strip_if_nonascii_arg(pattern: str, replacement: str, s: str) -> str:
    def repl(m):
        arg = m.group(1)
        return replacement if any(ord(ch)>127 for ch in arg) else m.group(0)
    import re
    return re.sub(pattern, repl, s)

src = strip_if_nonascii_arg(r"QLabel\(\"([^\"]*)\"\)", "QLabel('')", src)
src = strip_if_nonascii_arg(r"QPushButton\(\"([^\"]*)\"\)", "QPushButton('')", src)
src = strip_if_nonascii_arg(r"QCheckBox\(\"([^\"]*)\"\)", "QCheckBox('')", src)

Path('kiosk_app/main.py').write_text(src, encoding='utf-8')
print('fix applied')
