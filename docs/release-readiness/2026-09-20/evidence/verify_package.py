"""Verify an exact release ZIP using only synthetic files in a fresh directory."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

release = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
destination.mkdir(parents=True, exist_ok=False)
zip_path = release / "FileAssistant-0.1.0-rc1-windows-x64.zip"
checksums = {}
for line in (release / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    expected, name = line.split("  ", 1)
    actual = hashlib.sha256((release / name).read_bytes()).hexdigest()
    assert actual == expected
    checksums[name] = actual
with zipfile.ZipFile(zip_path) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    for name in names:
        parts = Path(name).parts
        assert not any(p in {".env", "settings.json", ".git", ".venv", ".build-venv", ".file_assistant_backups"} for p in parts), name
        assert name == "FileAssistant/_internal/docx/templates/default.docx" or not name.endswith((".docx", ".xlsx", ".pdf", ".log")), name
        assert not Path(name).is_absolute() and ".." not in parts
    assert not any(n.lower().endswith("/icuuc.dll") for n in names)
    assert any(n.endswith("qwindows.dll") for n in names)
    assert any(n.endswith("python312.dll") for n in names)
    assert any(n.endswith("cacert.pem") for n in names)
    assert any("THIRD_PARTY_LICENSES" in n for n in names)
    archive.extractall(destination / "中文 空格解压目录")
bundle = destination / "中文 空格解压目录/FileAssistant"
manifest = json.loads((bundle / "BUILD_INFO.json").read_text(encoding="utf-8"))
with zipfile.ZipFile(release / "FileAssistant-0.1.0-rc1-source.zip") as archive:
    for name, digest in manifest["source_files_sha256"].items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
environment = os.environ.copy()
for key in list(environment):
    if key.startswith(("PYTHON", "DEEPSEEK")) or key in {"VIRTUAL_ENV", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"}:
        environment.pop(key)
environment["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
environment["QT_QPA_PLATFORM"] = "windows"
environment["LOCALAPPDATA"] = str(destination / "独立用户目录")
exe = bundle / "文件小助手.exe"
result_dir = destination / "frozen-self-test"
completed = subprocess.run([str(exe), "--self-test", str(result_dir)], cwd=destination,
                           env=environment, timeout=120)
result = json.loads((result_dir / "result.json").read_text(encoding="utf-8"))
report = {"zip_checksums": checksums, "zip_members": len(names), "source_id": manifest["source_id"],
          "frozen_exit_code": completed.returncode, "frozen_result": result,
          "path_only_system32": True, "python_environment_removed": True,
          "zip_integrity_and_manifest": "passed", "private_file_name_scan": "passed",
          "limitations": ["developer machine still has Python installed", "not real user interaction", "no live AI account"]}
(destination / "package-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
assert completed.returncode == 0 and result["status"] == "passed"
print(json.dumps(report, ensure_ascii=False, indent=2))

