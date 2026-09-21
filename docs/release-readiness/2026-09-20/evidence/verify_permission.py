"""Real Windows directory write denial, only on a newly created synthetic directory."""
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=False)
folder = root / '不可写 中文目录'
folder.mkdir()
repository = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repository))
source = folder / '合成 文档.docx'
shutil.copy2(repository / 'tests/sample_files/会议通知.docx', source)
before = hashlib.sha256(source.read_bytes()).hexdigest()
sid_csv = subprocess.check_output(['whoami', '/user', '/fo', 'csv', '/nh'], text=True)
sid = next(csv.reader(io.StringIO(sid_csv.strip())))[1]
os.environ['LOCALAPPDATA'] = str(root / '独立用户数据')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from app.operations.schemas import validate_operation_plan
from app.config.settings import DeepSeekSettings
import app.ui.main_window as ui
application = QApplication([])
plan = validate_operation_plan({'explanation': '合成验收', 'operations': [{'action': 'append_text', 'text': '合成新增文字'}]})
class FakeClient:
    def __init__(self, *args): pass
    def close(self): pass
ui.DeepSeekClient = FakeClient
ui.DeepSeekSettings.from_environment = lambda: DeepSeekSettings(api_key='synthetic')
ui.IntentParser.parse = lambda *args: plan
window = ui.MainWindow()
window.select_file(source)
window.request_input.setText('增加合成文字')
window._confirm_modification = lambda *args: True
shown = []
window._show_message = lambda title, text, *args: shown.append((title, text))
denied = False
try:
    subprocess.run(['icacls', str(folder), '/deny', f'*{sid}:(W)'], check=True, capture_output=True)
    denied = True
    window.handle_start()
    assert shown and '写入权限' in shown[-1][1], shown
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    # Check directory contents after restoring its ACL.
    report = {'status': 'passed', 'method': 'real Windows ACL deny write on fresh synthetic directory',
              'dialog': shown[-1], 'source_sha256_unchanged': before, 'ai': 'simulated validated plan; no network',
              'interaction': 'programmatic Qt handler; not human desktop interaction'}
finally:
    if denied:
        subprocess.run(['icacls', str(folder), '/remove:d', f'*{sid}'], check=True, capture_output=True)
    window.close()
assert list(folder.iterdir()) == [source]
(root / 'permission-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))

