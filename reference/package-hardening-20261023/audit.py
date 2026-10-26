"""Read source locks and an existing module archive or mounted/staged root only."""
from pathlib import Path
import argparse
import json
import stat
from hardening import audit_sources, load_lock, load_modules, require, sha, validate_module


def audit_root(root, lock):
    require(root.is_absolute() and root.is_dir(), 'Use an absolute existing root')
    rows = []
    for record in lock['files'] + lock['modules']:
        path = root / record['target']
        require(path.is_file() and not path.is_symlink(), 'Missing or nonregular target: ' + record['target'])
        data = path.read_bytes()
        require(sha(data) == record['sha256'], 'Installed payload differs: ' + record['target'])
        mode = stat.S_IMODE(path.stat().st_mode)
        require(mode == record['mode'], 'Unexpected installed mode: ' + record['target'])
        if 'name' in record:
            validate_module(data, record, lock)
        rows.append(dict(target=record['target'], sha256=sha(data), mode=mode))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module-archive', type=Path)
    parser.add_argument('--root', type=Path, help='Read-only comparison with a mounted root; / reads local device only')
    parser.add_argument('--output', type=Path, help='Optional explicitly selected report path')
    args = parser.parse_args()
    lock = load_lock()
    sources = audit_sources(lock)
    modules = load_modules(args.module_archive, lock) if args.module_archive else {}
    report = dict(schema=1, source_audit_passed=True, sources=sources,
                  module_archive_audited=bool(modules),
                  modules=[validate_module(modules[r['name']], r, lock) for r in lock['modules']] if modules else [],
                  installed_root_audited=bool(args.root),
                  installed_files=audit_root(args.root, lock) if args.root else [],
                  device_actions_performed=False, installation_or_functionality_proven=False)
    text = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(text)
    print(text, end='')


if __name__ == '__main__':
    main()
