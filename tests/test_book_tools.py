"""Behavioural checks use only synthetic files in isolated temporary folders."""
import copy
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'architecture-concept-book'
SPEC = importlib.util.spec_from_file_location('book_tools', SKILL / 'scripts/book_tools.py')
TOOLS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOLS)


class ManifestChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'exercise'
        shutil.copytree(SKILL / 'assets/example', self.root)
        self.manifest = TOOLS.read(self.root / 'project.json')

    def tearDown(self):
        self.temp.cleanup()

    def result(self, release=False):
        return TOOLS.check(self.manifest, self.root, release)

    def fact(self, name):
        return next(f for f in self.manifest['facts'] if f['id'] == name)

    def test_example_retains_unknown_and_checks_formulas(self):
        result = self.result()
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['derived_facts_checked'], 2)
        self.assertIsNone(self.fact('parking')['value'])
        self.assertTrue(result['mechanical_only'])
        self.assertFalse(result['visual_review_performed_by_tool'])

    def test_starter_is_not_a_finished_book(self):
        result = TOOLS.check(TOOLS.read(SKILL / 'assets/project-template.json'), self.root)
        self.assertTrue(result['valid'])
        self.assertTrue(result['warnings'])
        self.assertFalse(TOOLS.check(TOOLS.read(SKILL / 'assets/project-template.json'), self.root, True)['valid'])

    def test_replaced_source_is_rejected(self):
        (self.root / 'brief.md').write_text('changed source', encoding='utf-8')
        self.assertFalse(self.result()['valid'])

    def test_wrong_ratio_and_zero_denominator_are_rejected(self):
        self.fact('far')['value'] = 5
        self.assertFalse(self.result()['valid'])
        self.fact('far')['value'] = 3.6
        self.fact('site')['value'] = 0
        self.assertTrue(any('zero denominator' in e for e in self.result()['errors']))

    def test_formula_cycle_is_rejected(self):
        self.fact('far')['formula']['inputs'] = ['far', 'site']
        self.assertTrue(any('cycle' in e for e in self.result()['errors']))

    def test_missing_reference_and_duplicate_id_are_rejected(self):
        self.manifest['pages'][0]['figure_ids'] = ['absent']
        self.manifest['schemes'].append(copy.deepcopy(self.manifest['schemes'][0]))
        result = self.result()
        self.assertFalse(result['valid'])
        self.assertTrue(any('missing figures' in e for e in result['errors']))
        self.assertTrue(any('Duplicate ID' in e for e in result['errors']))

    def test_count_is_integer_and_unknown_is_not_zero(self):
        self.fact('homes')['value'] = 120.5
        self.fact('parking')['value'] = 0
        self.assertFalse(self.result()['valid'])

    def test_generated_image_cannot_supply_measurement(self):
        self.manifest['sources'][0]['kind'] = 'generated_image'
        self.assertTrue(any('measurement authority' in e for e in self.result()['errors']))

    def test_cross_root_path_is_rejected(self):
        self.manifest['sources'][0]['path'] = '../outside.md'
        self.assertFalse(self.result()['valid'])

    def test_multiple_schemes_need_no_fixed_count(self):
        self.manifest['schemes'].append({'id': 'B', 'name': 'Synthetic second scheme'})
        page = copy.deepcopy(self.manifest['pages'][0])
        page.update(id='P-second', order=3, scheme_ids=['B'], figure_ids=[])
        self.manifest['pages'].append(page)
        self.assertTrue(self.result()['valid'])

    def release_fixture(self):
        self.manifest['phase'] = 'delivery'
        (self.root / 'final.txt').write_text('Synthetic output for hash-binding tests, not a PDF.', encoding='utf-8')
        (self.root / 'review.txt').write_text('Synthetic review evidence for test mechanics only.', encoding='utf-8')
        digest = TOOLS.sha(self.root / 'final.txt')
        self.manifest['deliverables'] = [{'id': 'D1', 'kind': 'editable', 'path': 'final.txt', 'sha256': digest,
            'source_snapshot': [{'source_id': 'S1', 'sha256': self.manifest['sources'][0]['sha256']}]}]
        self.manifest['checks'] = [{'kind': kind, 'status': 'pass', 'target_id': 'D1', 'target_sha256': digest,
            'evidence_path': 'review.txt', 'evidence_sha256': TOOLS.sha(self.root / 'review.txt'),
            'observations': 'Synthetic evidence tests only; no real visual acceptance asserted.'}
            for kind in ['content', 'numeric', 'visual', 'delivery']]

    def test_release_requires_current_evidence_and_cannot_skip_visual(self):
        self.release_fixture()
        self.assertTrue(self.result(True)['valid'])
        self.manifest['checks'][2]['status'] = 'not_run'
        self.assertFalse(self.result(True)['valid'])
        self.manifest['checks'][2]['status'] = 'not_applicable'
        self.assertFalse(self.result(True)['valid'])

    def test_changed_output_invalidates_release(self):
        self.release_fixture()
        original = (self.root / 'final.txt').read_bytes()
        (self.root / 'final.txt').write_text('rebuilt output', encoding='utf-8')
        self.assertFalse(self.result(True)['valid'])
        (self.root / 'final.txt').write_bytes(original)
        (self.root / 'review.txt').write_text('changed evidence', encoding='utf-8')
        self.assertFalse(self.result(True)['valid'])

    def test_snapshot_and_planned_figure_block_release(self):
        self.release_fixture()
        self.manifest['deliverables'][0]['source_snapshot'] = []
        self.manifest['figures'][0]['status'] = 'planned'
        self.assertFalse(self.result(True)['valid'])

    def test_inventory_hash_and_no_overwrite(self):
        result = TOOLS.inventory(self.root, True)
        self.assertTrue(result['files'])
        self.assertTrue(all(len(f['sha256']) == 64 for f in result['files']))
        self.assertFalse(result['content_read'])
        out = self.root / 'inventory.json'
        TOOLS.write_json(out, result)
        with self.assertRaises(FileExistsError):
            TOOLS.write_json(out, result)


if __name__ == '__main__':
    unittest.main()
