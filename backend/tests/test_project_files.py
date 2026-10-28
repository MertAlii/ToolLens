from pathlib import Path
import json
import threading
import time
from unittest.mock import patch
import pytest
from backend import providers
from backend.project_files import tree,index,read_file,resolve_paths,prepare_question,MAX_CONTEXT
from backend.project_chat import ProjectChat
from backend.storage import Store
from backend.core import Workbench


def test_tree_is_hierarchical_and_hides_dependencies_and_credentials(tmp_path):
    (tmp_path/'src').mkdir();(tmp_path/'src'/'server.py').write_text('print(1)')
    (tmp_path/'README.md').write_text('read me')
    for name in ('.env','auth.json','private.key'):(tmp_path/name).write_text('private')
    (tmp_path/'node_modules').mkdir()
    rows=tree(tmp_path)['entries']
    assert [r['path'] for r in rows]==['src','README.md']
    assert tree(tmp_path,'src')['entries'][0]['path']=='src/server.py'
    assert {p['path'] for p in index(tmp_path)['files']}=={'src/server.py','README.md'}


@pytest.mark.parametrize('path',['../private.txt','/etc/passwd','C:/private.txt','src/../../private.txt','.env','auth.json','folder\\secret.py'])
def test_file_reads_cannot_escape_project_or_open_hidden_secrets(tmp_path,path):
    with pytest.raises(ValueError):read_file(tmp_path,path)


def test_symlinked_file_is_never_followed(tmp_path):
    root=tmp_path/'project';root.mkdir();secret=tmp_path/'secret.py';secret.write_text('private')
    try:(root/'alias.py').symlink_to(secret)
    except OSError:pytest.skip('Symlink creation unavailable')
    assert tree(root)['entries']==[]
    with pytest.raises(ValueError):read_file(root,'alias.py')


def test_binary_content_is_not_returned_as_source(tmp_path):
    (tmp_path/'binary.py').write_bytes(b'a\x00b')
    with pytest.raises(ValueError,match='İkili'):read_file(tmp_path,'binary.py')


def test_project_cannot_be_hidden_while_file_answer_is_running(tmp_path):
    wb=Workbench(tmp_path/'data')
    try:
        root=wb.roots[0]/'project';root.mkdir()
        p=wb.add_project('project',str(root))
        wb.store.put('file_chat',{'id':'question','project_id':p['id'],'status':'running'})
        with pytest.raises(ValueError,match='dosya sorusu'):wb.archive_project(p['id'])
        assert wb.project(p['id']) is not None
    finally:wb.close()


def test_mentions_resolve_spaces_multiple_files_and_ignore_email():
    assert resolve_paths('@src/server.py ile @{docs/proje notu.md} ilişkisi nedir? mert@example.com',['src/server.py'])==['src/server.py','docs/proje notu.md']
    with pytest.raises(ValueError):resolve_paths('Dosyasız soru',[])
    with pytest.raises(ValueError):resolve_paths('Soru',[str(i)+'.py' for i in range(7)])


def test_evidence_reference_can_cross_contiguous_source_chunks():
    context={'sources':[{'path':'server.py','range':{'start_line':1,'end_line':90}},{'path':'server.py','range':{'start_line':91,'end_line':147}}]}
    response={'content':'Kaynak açıklaması','evidence_refs':[{'path':'server.py','start_line':80,'end_line':120}],'uncertainties':[],'patch':None}
    assert providers._parse_payload(response,context,'explain')['evidence_refs']==response['evidence_refs']


def test_evidence_reference_cannot_bridge_missing_source_lines():
    context={'sources':[{'path':'server.py','range':{'start_line':1,'end_line':20}},{'path':'server.py','range':{'start_line':40,'end_line':60}}]}
    response={'content':'Kaynak açıklaması','evidence_refs':[{'path':'server.py','start_line':15,'end_line':45}],'uncertainties':[],'patch':None}
    with pytest.raises(providers.ProviderError):providers._parse_payload(response,context,'explain')


def test_selected_files_only_are_supplied_and_long_content_is_not_silently_cut(tmp_path):
    (tmp_path/'selected.py').write_text(('value=1\n'*2500)+'TAIL_MARKER',encoding='utf-8')
    (tmp_path/'not_selected.py').write_text('MUST_NOT_BE_SENT')
    original=(tmp_path/'selected.py').read_bytes()
    files,context=prepare_question(tmp_path,'@selected.py ne yapıyor?',[])
    sanitized=providers._sanitize_context(context)
    packet=json.dumps(sanitized)
    assert 'TAIL_MARKER' in packet and 'MUST_NOT_BE_SENT' not in packet
    assert len(context['sources'])>1
    assert (tmp_path/'selected.py').read_bytes()==original
    assert files[0]['hash']
    (tmp_path/'huge.py').write_text('a'*(MAX_CONTEXT+1))
    with pytest.raises(ValueError,match='30 KB'):prepare_question(tmp_path,'@huge.py ne yapıyor?',[])


def test_reference_to_unselected_file_is_rejected(tmp_path):
    (tmp_path/'a.py').write_text('print(1)')
    _,context=prepare_question(tmp_path,'@a.py ne yapıyor?',[])
    response={'content':'test','evidence_refs':[{'path':'other.py','start_line':1,'end_line':1}],'uncertainties':[],'patch':None}
    with pytest.raises(providers.ProviderError):providers._parse_payload(response,context,'explain')


def test_chat_retains_original_file_copy_and_provider_after_source_changes(tmp_path):
    (tmp_path/'server.py').write_text('original = 1')
    manager=ProjectChat(Store(tmp_path/'data'/'db.sqlite'))
    answer={'provider':'codex','model':'test-model','status':'completed','content':'Yanıt','evidence_refs':[{'path':'server.py','start_line':1,'end_line':1}],'uncertainties':[],'patch':None}
    try:
        with patch.object(providers,'generate',return_value=answer) as generated:
            result=manager.start({'id':'p'},tmp_path,'@server.py anlat',[],'codex','test-model',{})
            for _ in range(100):
                current=manager.get('p',result['id'])
                if current['status'] not in ('queued','running'):break
                time.sleep(.01)
            assert current['status']=='completed'
            assert generated.call_args.args[3]['sources'][0]['snippet']=='original = 1'
        (tmp_path/'server.py').write_text('changed = 2')
        assert manager.get('p',result['id'])['source_copies'][0]['content']=='original = 1'
        assert manager.history('p')[0]['provider']=='codex'
        assert 'source_copies' not in manager.history('p')[0]
        assert manager.cancel('p',result['id'])['status']=='completed'
        assert not manager.get('p',result['id']).get('cancellation_requested')
        with pytest.raises(KeyError):manager.get('other-project',result['id'])
    finally:manager.close()


def test_followup_context_uses_only_same_project_model_and_unchanged_files(tmp_path):
    (tmp_path/'server.py').write_text('pass')
    manager=ProjectChat(Store(tmp_path/'data'/'db.sqlite'))
    source=read_file(tmp_path,'server.py')
    base={'project_id':'p','question':'Eski soru','content':'Eski yanıt','status':'completed','provider':'codex','model':'test-model','files':[source]}
    manager.store.put('file_chat',{'id':'good',**base})
    manager.store.put('file_chat',{'id':'other-model',**base,'model':'other'})
    manager.store.put('file_chat',{'id':'other-project',**base,'project_id':'other'})
    manager.store.put('file_chat',{'id':'changed',**base,'files':[{**source,'hash':'different'}]})
    response={'provider':'codex','model':'test-model','status':'completed','content':'Yanıt','evidence_refs':[],'uncertainties':[],'patch':None}
    try:
        with patch.object(providers,'generate',return_value=response) as generated:
            result=manager.start({'id':'p'},tmp_path,'@server.py önceki açıklamayı açar mısın?',[],'codex','test-model',{})
            for _ in range(100):
                if manager.get('p',result['id'])['status']=='completed':break
                time.sleep(.01)
            assert generated.call_args.args[3]['previous_messages']==[{'question':'Eski soru','answer':'Eski yanıt'}]
    finally:manager.close()


def test_file_question_can_be_cancelled_without_success_result(tmp_path):
    (tmp_path/'server.py').write_text('pass')
    manager=ProjectChat(Store(tmp_path/'data'/'db.sqlite'))
    def wait(*args,**kwargs):
        kwargs['cancel_event'].wait(2)
        raise providers.ProviderError('cancelled')
    try:
        with patch.object(providers,'generate',side_effect=wait):
            result=manager.start({'id':'p'},tmp_path,'@server.py anlat',[],'codex','test-model',{})
            manager.cancel('p',result['id'])
            for _ in range(100):
                current=manager.get('p',result['id'])
                if current['status']=='cancelled':break
                time.sleep(.01)
            assert current['status']=='cancelled' and not current['content']
    finally:manager.close()


def test_general_chat_does_not_read_project_files(tmp_path):
    (tmp_path/'private.py').write_text('PRIVATE_CONTENT_MUST_NOT_BE_READ')
    files,context=prepare_question(tmp_path,'Merhaba, MCP nedir?',[],allow_empty=True)
    assert files==[] and context['sources']==[]
    assert 'PRIVATE_CONTENT' not in json.dumps(context)
    prompt=providers._prompt('chat',context,'simple')
    assert 'İlk cümlede Risk bulundu' not in prompt
    assert 'Genel soruda zorla risk' in prompt
