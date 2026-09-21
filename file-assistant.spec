# Full onedir bundle. PyInstaller's Qt hook collects the Windows platform plugin.
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['app/main.py'], pathex=[SPECPATH],
    datas=collect_data_files('docx') + collect_data_files('certifi'),
    hiddenimports=['pymupdf', 'openpyxl', 'pydantic'],
    excludes=['pytest', 'tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
    noarchive=False,
)
# Qt uses the ICU supplied by supported Windows versions. A similarly named
# third-party ICU (e.g. Poppler) exports incompatible symbols and must not shadow it.
a.binaries = [entry for entry in a.binaries if entry[0].replace('\\', '/').rsplit('/', 1)[-1].lower() != 'icuuc.dll']
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='文件小助手',
          debug=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FileAssistant')
