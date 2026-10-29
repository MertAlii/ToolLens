import sqlite3
import pytest
from backend.storage import Store
from backend.analysis import inventory

def test_database_is_closed_on_success_and_failure(tmp_path):
    store=Store(tmp_path/'records.sqlite')
    with store.connect() as db:
        db.execute('SELECT 1')
    with pytest.raises(sqlite3.ProgrammingError):db.execute('SELECT 1')
    with pytest.raises(RuntimeError):
        with store.connect() as failed:
            failed.execute("INSERT INTO records VALUES ('x','y','{}')")
            raise RuntimeError('rollback')
    with pytest.raises(sqlite3.ProgrammingError):failed.execute('SELECT 1')
    assert store.get('x','y') is None

def test_context_is_injected_and_keyword_only_inputs_are_preserved():
    source='''from mcp.server.fastmcp import Context as Ctx
@mcp.tool()
async def search(query: str, ctx: Ctx, limit: int=5, *, exact: bool, extra: str=''):
    pass
'''
    tools,_=inventory({'server.py':source})
    schema=tools[0]['input_schema']
    assert set(schema['properties'])=={'query','limit','exact','extra'}
    assert schema['required']==['query','exact']

def test_deletion_has_source_evidence_without_runtime_claim():
    tools,_=inventory({'server.py':'''import os as system
from shutil import rmtree as remove_tree
from pathlib import Path
@mcp.tool()
def clean():
    system.remove('one.txt')
    remove_tree('cache')
    Path('two.txt').unlink()
'''})
    accesses=tools[0]['accesses']['filesystem.write']
    assert [x['target'] for x in accesses]==['one.txt','cache','two.txt']
    assert all(x['evidence']['start_line'] for x in accesses)
