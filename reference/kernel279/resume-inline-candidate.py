"""Resume at the recorded patch, skipping only exact reverse-applicable changes."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parent
PATH = ROOT / 'inline-candidate-apply-validation.json'
result = json.loads(PATH.read_text())
tree = result['candidate']
patches = Path('/mnt/e/edk2-samurai-out/kernel279/posted-patches')
result.setdefault('already_present', [])
result.setdefault('adapted', [])
result.pop('first_conflict', None)
for item in result['patches']:
    number = item['number']
    if number in result['applied'] + result['already_present'] + result['adapted']:
        continue
    path = str(patches / f'{number:02d}.patch')
    command = ['git', '-C', tree, 'apply']
    forward = subprocess.run(command + ['--check', path], capture_output=True, text=True)
    if forward.returncode == 0:
        subprocess.run(command + [path], check=True, capture_output=True)
        result['applied'].append(number)
    else:
        reverse = subprocess.run(command + ['--reverse', '--check', path],
                                 capture_output=True, text=True)
        if reverse.returncode == 0:
            result['already_present'].append(number)
        else:
            result['first_conflict'] = dict(number=number, stderr=forward.stderr)
            break
PATH.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'patches'}, indent=2))
