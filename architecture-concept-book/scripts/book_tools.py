"""Source inventory, concept-book manifest checks and read-only PDF rendering."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else _stream_sha(stream)


def _stream_sha(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value, overwrite=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w' if overwrite else 'x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def within(root, value):
    relative = Path(value)
    if relative.is_absolute() or relative.drive or '..' in relative.parts:
        raise ValueError('Use a relative path inside the selected workspace: ' + value)
    resolved = (root / relative).resolve()
    resolved.relative_to(root.resolve())
    return resolved


def inventory(root, hash_files=False, exclude=None):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Inventory root is not a directory')
    rows, skipped, skipped_dirs = [], [], []
    for directory, dirs, files in os.walk(root, followlinks=False):
        retained = []
        for name in sorted(dirs):
            path = Path(directory) / name
            linked = path.is_symlink() or getattr(path, 'is_junction', lambda: False)()
            if name in {'.git', '.venv', 'venv', 'node_modules', '__pycache__'} or linked:
                skipped_dirs.append(path.relative_to(root).as_posix())
            else:
                retained.append(name)
        dirs[:] = retained
        for name in sorted(files):
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink() or name.startswith('.env') or (exclude and path.resolve() == Path(exclude).resolve()):
                skipped.append(rel)
                continue
            stat = path.stat()
            row = {'path': rel, 'suffix': path.suffix.lower(), 'bytes': stat.st_size,
                   'modified_utc': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}
            if hash_files:
                row['sha256'] = sha(path)
            rows.append(row)
    return {'root_label': root.name, 'files': rows, 'skipped_files': skipped, 'skipped_directories': skipped_dirs, 'content_read': False}


def check(manifest, root, release=False):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError('Manifest checks require jsonschema; install scripts/requirements.txt') from exc
    root = Path(root).resolve()
    schema = read(Path(__file__).resolve().parents[1] / 'assets/project-manifest.schema.json')
    errors = ['schema: ' + e.message for e in Draft202012Validator(schema).iter_errors(manifest)]
    warnings = []
    if errors:
        return {'valid': False, 'mechanical_only': True, 'errors': errors, 'warnings': warnings}
    tables = {}
    for group in ['sources', 'schemes', 'facts', 'figures', 'pages', 'deliverables']:
        tables[group] = {}
        for item in manifest[group]:
            if item['id'] in tables[group]:
                errors.append('Duplicate ID in ' + group + ': ' + item['id'])
            tables[group][item['id']] = item
    sources, facts = tables['sources'], tables['facts']

    def refs(ids, group, context):
        for ident in ids:
            if ident not in tables[group]:
                errors.append(context + ': missing ' + group + ' ID ' + ident)

    def file_check(path, digest, context):
        try:
            target = within(root, path)
            if not target.is_file():
                raise ValueError('file missing')
            if not digest or sha(target) != digest:
                raise ValueError('SHA256 missing or changed')
        except (ValueError, OSError) as exc:
            errors.append(context + ': ' + str(exc))

    for source in manifest['sources']:
        if source['status'] == 'read':
            file_check(source['path'], source['sha256'], source['id'])
        else:
            (errors if release else warnings).append(source['id'] + ': source is ' + source['status'])
    for fact in facts.values():
        context = fact['id']
        refs(fact['source_ids'], 'sources', context)
        if fact.get('scheme_id') is not None:
            refs([fact['scheme_id']], 'schemes', context)
        value = fact['value']
        if fact['status'] == 'unknown':
            if value is not None:
                errors.append(context + ': unknown must have null value')
            (errors if release and fact.get('blocking_unknown') else warnings).append(context + ': unknown')
        elif value is None:
            errors.append(context + ': non-unknown value cannot be null')
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(context + ': non-finite number')
        if fact['quantity_kind'] == 'count' and value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            errors.append(context + ': a count must be an integer')
        if fact['status'] == 'source' and (not fact['source_ids'] or not fact['locator'].strip()):
            errors.append(context + ': source fact needs source IDs and locator')
        if fact['quantity_kind'] != 'text' and fact['status'] == 'source':
            if any(sources.get(i, {}).get('kind') == 'generated_image' for i in fact['source_ids']):
                errors.append(context + ': generated image cannot be measurement authority')
        if fact['status'] == 'derived' and not fact.get('formula'):
            errors.append(context + ': derived fact needs formula')

    visited = set()

    def evaluate(ident, active):
        if ident not in facts:
            raise ValueError('missing fact ' + ident)
        if ident in active:
            raise ValueError('formula cycle at ' + ident)
        fact = facts[ident]
        formula = fact.get('formula')
        if not formula:
            return fact['value']
        values = [evaluate(i, active | {ident}) for i in formula['inputs']]
        if any(v is None for v in values):
            if fact['value'] is not None:
                raise ValueError(ident + ': unknown inputs cannot yield a known result')
            return None
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in values):
            raise ValueError(ident + ': formula inputs must be numbers')
        op = formula['op']
        if op in {'difference', 'ratio', 'percent'} and len(values) != 2:
            raise ValueError(ident + ': operation requires two inputs')
        if op == 'sum':
            result = sum(values)
        elif op == 'product':
            result = math.prod(values)
        elif op == 'difference':
            result = values[0] - values[1]
        else:
            if values[1] == 0:
                raise ValueError(ident + ': zero denominator')
            result = values[0] / values[1] * (100 if op == 'percent' else 1)
        actual = fact['value']
        if not isinstance(actual, (int, float)) or isinstance(actual, bool) or not math.isclose(actual, result, rel_tol=1e-9, abs_tol=formula.get('tolerance', 1e-6)):
            raise ValueError(ident + ': stored result disagrees with unrounded formula')
        visited.add(ident)
        return result

    for ident in facts:
        try:
            evaluate(ident, set())
        except ValueError as exc:
            errors.append(str(exc))
    for figure in manifest['figures']:
        refs(figure['source_ids'], 'sources', figure['id'])
        refs(figure['scheme_ids'], 'schemes', figure['id'])
        if figure['status'] == 'ready':
            file_check(figure['path'], figure['sha256'], figure['id'])
    orders = [page['order'] for page in manifest['pages']]
    if len(set(orders)) != len(orders):
        errors.append('Duplicate page order')
    for page in manifest['pages']:
        for field, group in [('source_ids', 'sources'), ('scheme_ids', 'schemes'), ('figure_ids', 'figures'), ('fact_ids', 'facts')]:
            refs(page.get(field, []), group, page['id'])
        if release:
            for figure_id in page['figure_ids']:
                if tables['figures'].get(figure_id, {}).get('status') != 'ready':
                    errors.append(page['id'] + ': referenced figure not ready: ' + figure_id)
    for deliverable in manifest['deliverables']:
        file_check(deliverable['path'], deliverable['sha256'], deliverable['id'])
        if release:
            expected = {i: s['sha256'] for i, s in sources.items() if s['status'] == 'read'}
            actual = {s['source_id']: s['sha256'] for s in deliverable['source_snapshot']}
            if actual != expected:
                errors.append(deliverable['id'] + ': input snapshot is incomplete or stale')
    for item in manifest['checks']:
        target = tables['deliverables'].get(item['target_id'])
        if not target or item['target_sha256'] != target['sha256']:
            errors.append('Check target missing or SHA mismatch: ' + item['kind'])
        if item['status'] == 'pass':
            file_check(item['evidence_path'], item['evidence_sha256'], 'check ' + item['kind'])
            if not item['observations'].strip():
                errors.append('Passing check needs observations: ' + item['kind'])
        if item['status'] == 'not_applicable' and not item['observations'].strip():
            errors.append('Not-applicable check needs a reason: ' + item['kind'])
    if release:
        if manifest['phase'] != 'delivery' or not manifest['pages'] or not manifest['deliverables']:
            errors.append('Release needs delivery phase, pages and deliverables')
        targets = [d for d in manifest['deliverables'] if d['kind'] == 'pdf'] or manifest['deliverables']
        for target in targets:
            for kind in ['content', 'numeric', 'visual', 'delivery']:
                matches = [c for c in manifest['checks'] if c['target_id'] == target['id'] and c['kind'] == kind]
                if len(matches) != 1 or matches[0]['status'] not in {'pass', 'not_applicable'}:
                    errors.append(target['id'] + ': release check incomplete or duplicated: ' + kind)
                elif kind != 'numeric' and matches[0]['status'] != 'pass':
                    errors.append(target['id'] + ': required review cannot be skipped: ' + kind)
                elif kind == 'numeric' and matches[0]['status'] == 'not_applicable' and any(f['quantity_kind'] != 'text' and f['value'] is not None for f in facts.values()):
                    errors.append(target['id'] + ': numeric review is required for known quantities')
    if not manifest['pages'] or not manifest['sources']:
        warnings.append('Empty planning template; no finished book is implied')
    return {'valid': not errors, 'mechanical_only': True, 'release_mode': release,
            'phase': manifest['phase'], 'counts': {k: len(v) for k, v in tables.items()},
            'derived_facts_checked': len(visited), 'errors': errors, 'warnings': warnings,
            'visual_review_performed_by_tool': False}


def pdf_audit(path, render_dir, long_edge=1600):
    try:
        import pypdfium2 as pdfium
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError('PDF rendering requires pypdfium2 and Pillow') from exc
    path = Path(path).resolve()
    digest = sha(path)
    output = Path(render_dir)
    output.mkdir(parents=True, exist_ok=False)
    doc = pdfium.PdfDocument(path)
    rows, contacts, sheet = [], [], None
    try:
        for index in range(len(doc)):
            if index % 24 == 0:
                sheet = Image.new('RGB', (6 * 300, 4 * 250), '#e8e8e8')
            page = doc[index]
            text_page = page.get_textpage()
            text = text_page.get_text_range()
            text_page.close()
            width, height = page.get_size()
            bitmap = page.render(scale=long_edge / max(width, height))
            image = bitmap.to_pil().convert('RGB')
            bitmap.close()
            filename = 'page-%04d.png' % (index + 1)
            image.save(output / filename)
            thumb = image.copy()
            thumb.thumbnail((280, 220))
            x, y = (index % 6) * 300 + 10, ((index % 24) // 6) * 250 + 25
            sheet.paste(thumb, (x, y))
            ImageDraw.Draw(sheet).text((x, y - 18), 'P%d' % (index + 1), fill='#000000')
            rows.append({'page': index + 1, 'size_pt': [width, height], 'characters': len(text),
                         'first_lines': text.splitlines()[:3], 'render': filename})
            page.close()
            if index % 24 == 23 or index == len(doc) - 1:
                name = 'contact-%03d.png' % (index // 24 + 1)
                sheet.save(output / name)
                contacts.append(name)
    finally:
        doc.close()
    if sha(path) != digest:
        raise ValueError('Source PDF changed during read-only rendering')
    report = {'pdf_name': path.name, 'pdf_sha256': digest, 'page_count': len(rows),
              'pages': rows, 'contact_sheets': contacts, 'mechanical_only': True,
              'font_embedding_checked': False, 'visual_review_performed_by_tool': False}
    write_json(output / 'pdf-audit.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inv = commands.add_parser('inventory')
    inv.add_argument('root', type=Path)
    inv.add_argument('--hash', action='store_true')
    inv.add_argument('--out', required=True, type=Path)
    inv.add_argument('--overwrite', action='store_true')
    valid = commands.add_parser('check')
    valid.add_argument('manifest', type=Path)
    valid.add_argument('--root', type=Path)
    valid.add_argument('--release', action='store_true')
    valid.add_argument('--out', type=Path)
    valid.add_argument('--overwrite', action='store_true')
    pdf = commands.add_parser('pdf-audit')
    pdf.add_argument('pdf', type=Path)
    pdf.add_argument('--render-dir', type=Path, required=True)
    pdf.add_argument('--long-edge', type=int, default=1600)
    args = parser.parse_args()
    try:
        if args.command == 'inventory':
            result = inventory(args.root, args.hash, args.out)
            write_json(args.out, result, args.overwrite)
            summary = {'files': len(result['files']), 'content_read': False}
        elif args.command == 'check':
            result = check(read(args.manifest), args.root or args.manifest.parent, args.release)
            if args.out:
                write_json(args.out, result, args.overwrite)
            summary = result
        else:
            if not 200 <= args.long_edge <= 6000:
                raise ValueError('long-edge must be between 200 and 6000')
            result = pdf_audit(args.pdf, args.render_dir, args.long_edge)
            summary = {k: result[k] for k in ['pdf_sha256', 'page_count', 'mechanical_only', 'visual_review_performed_by_tool']}
        print(json.dumps(summary, ensure_ascii=True, indent=2, allow_nan=False))
        return 1 if summary.get('valid') is False else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
