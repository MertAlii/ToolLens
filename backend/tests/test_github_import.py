import io
import stat
import threading
import zipfile
import pytest
from backend.github_import import parse_repository,extract_source
from backend.github_import import source_roots,select_source_root
from backend.core import Workbench


@pytest.mark.parametrize('url',[
 'http://github.com/a/b','https://github.com.evil.test/a/b',
 'https://user:password@github.com/a/b','https://github.com/a/b/tree/main',
 'https://github.com/a/b?token=secret','https://github.com/a/..',
 'file:///tmp/repo','https://127.0.0.1/a/b',
])
def test_only_canonical_public_github_repository_addresses_are_accepted(url):
    with pytest.raises(ValueError):parse_repository(url)


def test_repository_git_suffix_and_trailing_slash():
    assert parse_repository('https://github.com/modelcontextprotocol/servers.git/')==('modelcontextprotocol','servers')


def archive_with(name,content=b'print(1)'):
    out=io.BytesIO()
    entry=zipfile.ZipInfo('placeholder')
    entry.filename=name
    with zipfile.ZipFile(out,'w') as archive:archive.writestr(entry,content)
    return out.getvalue()


@pytest.mark.parametrize('path',['repo/../../escape.py','/escape.py','repo/C:/escape.py','repo/dir\\escape.py','repo/NUL.txt','repo/hidden.'])
def test_archive_cannot_write_outside_fresh_project_or_use_windows_aliases(tmp_path,path):
    with pytest.raises(ValueError):extract_source(archive_with(path),tmp_path,threading.Event())
    assert list(tmp_path.iterdir())==[]


def test_symlink_archive_is_rejected(tmp_path):
    out=io.BytesIO();entry=zipfile.ZipInfo('repo/link.py');entry.create_system=3;entry.external_attr=(stat.S_IFLNK|0o777)<<16
    with zipfile.ZipFile(out,'w') as archive:archive.writestr(entry,'../../private')
    with pytest.raises(ValueError):extract_source(out.getvalue(),tmp_path,threading.Event())
    assert not (tmp_path/'link.py').exists()


def test_import_keeps_real_source_without_executing_setup(tmp_path):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        archive.writestr('repo-sha/src/server.py','raise RuntimeError("DO_NOT_RUN")')
        archive.writestr('repo-sha/setup.py','raise RuntimeError("DO_NOT_RUN_SETUP")')
        archive.writestr('repo-sha/.git/config','should skip')
    assert extract_source(out.getvalue(),tmp_path,threading.Event())==2
    assert (tmp_path/'src/server.py').read_text()=='raise RuntimeError("DO_NOT_RUN")'
    assert not (tmp_path/'.git').exists()


def test_cancelled_import_writes_no_files(tmp_path):
    event=threading.Event();event.set()
    with pytest.raises(InterruptedError):extract_source(archive_with('repo/server.py'),tmp_path,event)
    assert list(tmp_path.iterdir())==[]


def test_expanded_size_limit_is_checked_before_extraction(tmp_path,monkeypatch):
    import backend.github_import as module
    monkeypatch.setattr(module,'MAX_EXPANDED',10)
    with pytest.raises(ValueError,match='100 MB'):extract_source(archive_with('repo/server.py',b'x'*11),tmp_path,threading.Event())
    assert list(tmp_path.iterdir())==[]


def test_multiple_projects_are_discovered_without_importing_code(tmp_path):
    (tmp_path/'server').mkdir();(tmp_path/'client').mkdir()
    (tmp_path/'server'/'pyproject.toml').write_text('dependencies = ["mcp[cli]>=1.2.0"]')
    (tmp_path/'client'/'package.json').write_text('{"dependencies":{"@modelcontextprotocol/sdk":"1.0"}}')
    assert source_roots(tmp_path)==[{'path':'client','language':'TypeScript'},{'path':'server','language':'Python'}]


def test_select_imported_subproject_retains_repository_revision_and_bounds(tmp_path):
    wb=Workbench(tmp_path/'data')
    try:
        root=wb.roots[0]/'github-test';root.mkdir();(root/'server').mkdir()
        (root/'server'/'requirements.txt').write_text('mcp>=1.2.0')
        p=wb.add_project('repo',str(root));p.update(repository_root=str(root),repository_commit='a'*40);wb.store.put('project',p)
        selected=select_source_root(wb,p['id'],'server')
        assert selected['path']==str(root/'server')
        assert selected['repository_commit']=='a'*40
        with pytest.raises(ValueError):select_source_root(wb,p['id'],'../outside')
        wb.store.new('scan',project_id=p['id'],status='running')
        with pytest.raises(ValueError,match='devam'):select_source_root(wb,p['id'],'.')
    finally:wb.close()
