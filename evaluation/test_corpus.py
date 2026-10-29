"""Dataset contract tests, distinct from detection accuracy measurements."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

import run_evaluation

ROOT = Path(__file__).resolve().parent


class CorpusTests(unittest.TestCase):
    def test_security_pair_count_and_frozen_sources(self):
        cases = run_evaluation.verify_manifest('security_manifest')['cases']
        self.assertEqual(len(cases), 48)
        self.assertEqual(len({c['family'] for c in cases}), 6)
        self.assertEqual(sum(c['split'] == 'held_out' for c in cases), 24)
        for case in cases:
            data = (ROOT / case['path'] / 'server.py').read_bytes().replace(b'\r\n', b'\n')
            self.assertEqual(hashlib.sha256(data).hexdigest(), case['source_sha256'])
            ast.parse(data.decode())

    def test_every_variant_has_both_labels(self):
        grouped = {}
        for case in run_evaluation.verify_manifest('security_manifest')['cases']:
            grouped.setdefault((case['family'], case['variant']), set()).add(case['state'])
        self.assertEqual(len(grouped), 24)
        self.assertTrue(all(s == {'vulnerable', 'fixed'} for s in grouped.values()))

    def test_version_pair_counts(self):
        cases = run_evaluation.verify_manifest('version_manifest')['pairs']
        self.assertEqual(len(cases), 24)
        for group in ('benign', 'review_needed', 'ambiguous'):
            self.assertEqual(sum(x['group'] == group for x in cases), 8)

    def test_version_metadata_expectations_are_measured(self):
        rows = run_evaluation.version_measurements()
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(r['matches_expected'] for r in rows))


if __name__ == '__main__': unittest.main()
