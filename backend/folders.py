"""Read-only folder selection inside the configured project roots."""
from pathlib import Path
from .core import validate_path
import os
import subprocess
import threading

PICKER_LOCK=threading.Lock()


def pick_folder():
    if os.name!='nt':raise ValueError('Yerel klasör penceresi bu sürümde Windows üzerinde kullanılabilir. Aşağıdaki klasör listesini kullanın.')
    if not PICKER_LOCK.acquire(blocking=False):raise ValueError('Klasör seçme penceresi zaten açık.')
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-STA','-File',str(Path(__file__).with_name('folder-dialog.ps1'))],capture_output=True,encoding='utf-8',errors='replace',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise ValueError('Windows klasör seçme penceresi açılamadı. Klasör listesini kullanabilirsiniz.')
        selected=result.stdout.strip()
        if not selected:return None
        path=Path(selected)
        return validate_path(str(path),[path.resolve()])
    except subprocess.TimeoutExpired:raise ValueError('Klasör seçimi zaman aşımına uğradı. Tekrar deneyin.') from None
    finally:PICKER_LOCK.release()

HIDDEN = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.codex', '.agents', '.aws'}

def browse_folders(raw: str | None, roots: list[Path]) -> dict:
    roots = [p.resolve() for p in roots]
    if not raw:
        return {'path': None, 'name': 'Çalışma klasörleri', 'parent': None,
                'folders': [{'name': p.name or str(p), 'path': str(p)} for p in roots if p.is_dir()], 'truncated': False}
    path = validate_path(raw, roots)
    rows = []
    try:
        for item in path.iterdir():
            if item.name.startswith('.') or item.name in HIDDEN:
                continue
            if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
                continue
            try:
                if item.is_dir():
                    rows.append({'name': item.name, 'path': str(item)})
            except OSError:
                continue
    except OSError as exc:
        raise ValueError('Bu klasör okunamıyor. Başka bir çalışma klasörü seçin.') from exc
    parent = path.parent
    can_go_up = parent != path and any(parent.is_relative_to(root) for root in roots)
    rows.sort(key=lambda r: r['name'].casefold())
    return {'path': str(path), 'name': path.name, 'parent': str(parent) if can_go_up else None,
            'folders': rows[:200], 'truncated': len(rows) > 200}
