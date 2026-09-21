"""Windows x64 构建唯一入口：隔离依赖、完整 onedir ZIP、源码清单、哈希。"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0-rc1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"} or sys.version_info[:2] != (3, 12):
        raise SystemExit("请在 Windows x64 / Python 3.12 上构建。")
    python = ROOT / ".build-venv/Scripts/python.exe"
    if Path(sys.executable).resolve() != python.resolve():
        if not python.exists():
            subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".build-venv")], check=True)
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements-build.lock")], check=True)
        subprocess.run([str(python), str(Path(__file__).resolve())], check=True)
        return
    os.chdir(ROOT)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "release" / f"{VERSION}-{stamp}"
    output.mkdir(parents=True)
    source_files = [p for folder in ("app", "scripts", "tests") for p in (ROOT / folder).rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".py", ".docx", ".xlsx", ".pdf"}]
    source_files += [ROOT / p for p in ("file-assistant.spec", "requirements.txt", "requirements-build.lock", "README.md", "docs/便携版使用说明.md", "docs/safety.md")]
    hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(source_files)}
    source_id = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    head = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], text=True).strip()
    manifest = {"version": VERSION, "built_at_utc": stamp, "baseline_commit": head,
                "source_id": source_id, "source_files_sha256": hashes, "python": sys.version,
                "platform": platform.platform()}
    # Never collect same-named DLLs from unrelated software on the developer PATH.
    build_environment = os.environ.copy()
    build_environment["PATH"] = os.pathsep.join([str(python.parent), sys.base_prefix,
                                                str(Path(os.environ["SystemRoot"]) / "System32")])
    for key in ("PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
        build_environment.pop(key, None)
    with (output / "build.log").open("w", encoding="utf-8") as log:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                        "--distpath", str(output / "stage"), "--workpath", str(output / "work"),
                        "file-assistant.spec"], stdout=log, stderr=subprocess.STDOUT, env=build_environment, check=True)
    # Refuse to label a bundle with a snapshot that changed while it was built.
    if any(digest(ROOT / name) != value for name, value in hashes.items()):
        raise RuntimeError("构建期间源码发生变化，请重新构建。")
    bundle = output / "stage/FileAssistant"
    if not list(bundle.rglob("qwindows.dll")) or not list(bundle.rglob("python312.dll")):
        raise RuntimeError("缺少 Windows 平台插件或 Python 运行库。")
    shutil.copy2(ROOT / "docs/便携版使用说明.md", bundle / "使用说明.txt")
    (bundle / "BUILD_INFO.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(ROOT / "requirements-build.lock", bundle / "requirements-build.lock")
    licenses = bundle / "THIRD_PARTY_LICENSES"
    licenses.mkdir()
    for distribution in metadata.distributions():
        notice_dir = licenses / distribution.metadata["Name"]
        notice_dir.mkdir(exist_ok=True)
        (notice_dir / "PACKAGE-METADATA.txt").write_text((distribution.read_text("METADATA") or distribution.read_text("PKG-INFO") or distribution.metadata["Name"]), encoding="utf-8")
        for file in distribution.files or []:
            if any(word in file.name.lower() for word in ("license", "copying", "notice")) and distribution.locate_file(file).is_file():
                target = licenses / distribution.metadata["Name"] / str(file).replace("..", "_")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(distribution.locate_file(file), target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    (bundle / "第三方说明.txt").write_text(
        "包含 Python、PySide6/Qt、PyMuPDF、python-docx、openpyxl、pydantic、httpx 等组件。\n"
        "许可文本见 THIRD_PARTY_LICENSES，实际版本见 requirements-build.lock。\n"
        "PySide6/Qt 使用 LGPLv3/商业许可，PyMuPDF 使用 AGPLv3/商业许可。\n"
        "本项目尚未声明自身许可证。本包为预发布测试版；第三方组件的使用与再分发须遵循其许可。\n"
        "同批输出包含本项目准确源码快照；该快照不等于第三方组件全部对应源码。\n", encoding="utf-8")
    source_zip = output / f"FileAssistant-{VERSION}-source.zip"
    with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr("BUILD_INFO.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    archive_base = output / f"FileAssistant-{VERSION}-windows-x64"
    package = Path(shutil.make_archive(str(archive_base), "zip", output / "stage", "FileAssistant"))
    (output / "SHA256SUMS").write_text("".join(f"{digest(p)}  {p.name}\n" for p in (package, source_zip)), encoding="utf-8")
    (output / "BUILD_INFO.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
