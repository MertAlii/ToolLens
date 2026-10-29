import hashlib
import pytest
import run_evaluation

def test_manifest_accepts_crlf_but_rejects_content_change(tmp_path,monkeypatch):
    monkeypatch.setattr(run_evaluation,'ROOT',tmp_path)
    raw=b'{\n"cases": []\n}\n'
    (tmp_path/'sample.json').write_bytes(raw.replace(b'\n',b'\r\n'))
    (tmp_path/'sample.sha256').write_text(hashlib.sha256(raw).hexdigest())
    assert run_evaluation.verify_manifest('sample')=={'cases':[]}
    (tmp_path/'sample.json').write_bytes(b'{"cases": [1]}')
    with pytest.raises(ValueError):run_evaluation.verify_manifest('sample')
