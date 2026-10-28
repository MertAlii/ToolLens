from pathlib import Path
import pytest
from backend.folders import browse_folders


def test_picker_stays_in_configured_root_and_hides_internal_folders(tmp_path):
    root = tmp_path / 'projects'
    root.mkdir()
    for name in ['beta', 'Alpha', '.git', '.aws', 'node_modules']:
        (root / name).mkdir()
    (root / 'not-a-folder.txt').write_text('content')
    listing = browse_folders(str(root), [root])
    assert listing['parent'] is None
    assert [p['name'] for p in listing['folders']] == ['Alpha', 'beta']
    child = browse_folders(str(root / 'beta'), [root])
    assert child['parent'] == str(root)
    with pytest.raises(ValueError):
        browse_folders(str(tmp_path), [root])
    with pytest.raises(ValueError):
        browse_folders(str(root / '..'), [root])


def test_root_listing_and_missing_path(tmp_path):
    root = tmp_path / 'work'
    root.mkdir()
    listing = browse_folders(None, [root])
    assert listing['path'] is None
    assert listing['folders'] == [{'name': 'work', 'path': str(root)}]
    with pytest.raises(FileNotFoundError):
        browse_folders(str(root / 'absent'), [root])
