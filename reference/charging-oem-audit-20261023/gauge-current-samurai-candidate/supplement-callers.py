"""Read-only whole-tree literal CURRENT_NOW inventory; not runtime binding proof."""
from pathlib import Path
import hashlib, importlib.util, json, re, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('gauge_current_whole_tree_storage', REF / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
source = storage.mounted_build().parent / 'source354'
command = (['rg', '-l', '--glob', '*.c'] if shutil.which('rg') else ['grep', '-rl', '--include=*.c'])
search = subprocess.run([*command, 'POWER_SUPPLY_PROP_CURRENT_NOW', str(source)],
                        check=True, capture_output=True, text=True)
inventory = []
calls = []
for name in sorted(search.stdout.splitlines()):
    path = Path(name)
    text = path.read_text(errors='replace')
    inventory.append(dict(path=str(path.relative_to(source)), sha256=sha(path),
                          lines=[i for i, line in enumerate(text.splitlines(), 1)
                                 if 'POWER_SUPPLY_PROP_CURRENT_NOW' in line]))
    for match in re.finditer(r'(?:power_supply_get_property(?:_from_supplier)?|(?:->|\.)get_property)\s*\([^;]{0,400}?POWER_SUPPLY_PROP_CURRENT_NOW[^;]{0,240}?;', text, re.S):
        calls.append(dict(path=str(path.relative_to(source)), line=text[:match.start()].count('\n') + 1,
                          sha256=sha(path), excerpt=match.group()))
result = dict(passed=True, scope='whole fixed source354 tree, C files with literal enum; dynamic forwarding and userspace are separately reviewed',
              files_with_literal=inventory, direct_literal_get_calls=calls,
              runtime_binding_proven=False, phone_accessed=False, SDK_invoked=False, Git_invoked=False)
(HERE / 'supplement-callers.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(passed=True, files=len(inventory), direct_calls=len(calls))))
