"""Locate installed desktop dependencies even when the app has an older PATH."""
import os
import shutil
import subprocess
from pathlib import Path

def docker_binary():
    found=shutil.which('docker')
    if found:return found
    candidates=[]
    if os.name=='nt':
        for root in {Path(os.environ.get('ProgramFiles','C:/Program Files')),Path('C:/Program Files')}:
            candidates.append(root/'Docker/Docker/resources/bin/docker.exe')
        local=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))
        candidates.extend([local/'Docker/resources/bin/docker.exe',local/'Programs/Docker/Docker/resources/bin/docker.exe',local/'Programs/DockerDesktop/resources/bin/docker.exe',Path.home()/'AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'])
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
                for keypath in (r'Software\Microsoft\Windows\CurrentVersion\Uninstall',r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'):
                    try:
                        with winreg.OpenKey(hive,keypath) as parent:
                            for index in range(winreg.QueryInfoKey(parent)[0]):
                                try:
                                    with winreg.OpenKey(parent,winreg.EnumKey(parent,index)) as item:
                                        if winreg.QueryValueEx(item,'DisplayName')[0]=='Docker Desktop':
                                            candidates.append(Path(winreg.QueryValueEx(item,'InstallLocation')[0])/'resources/bin/docker.exe')
                                except OSError:continue
                    except OSError:continue
        except ImportError:pass
    return next((str(p) for p in candidates if p.is_file()),None)

def docker_status():
    binary=docker_binary()
    if not binary:return {'installed':False,'available':False,'message':'Docker CLI kurulumu bulunamadı.'}
    try:
        result=subprocess.run([binary,'info','--format','{{.ServerVersion}}'],capture_output=True,text=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        available=result.returncode==0
        return {'installed':True,'available':available,'version':result.stdout.strip() if available else None,'message':'Docker çalışıyor.' if available else 'Docker kurulu; Docker Desktop veya motor servisi çalışmıyor ya da erişilemiyor.'}
    except (OSError,subprocess.TimeoutExpired):return {'installed':True,'available':False,'message':'Docker kurulu; motor servisi yanıt vermedi.'}


def docker_environment():
    """Keep Docker Desktop credential helpers discoverable in child processes."""
    env=os.environ.copy();binary=docker_binary()
    if binary:env['PATH']=str(Path(binary).parent)+os.pathsep+env.get('PATH','')
    return env
