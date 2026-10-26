from pathlib import Path
import host,json,subprocess

here=Path(__file__).resolve().parent
host.upload(host.PRIVATE/'staging-manifest-private.json','/var/lib/samurai/k203-packages/staging-manifest-private.json')
try:p=host.ssh('python3 -',input=(here/'package-preflight.py').read_bytes(),timeout=150)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'package-preflight-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise SystemExit('Preflight failed; no package transaction requested, inspect private output')
(host.PRIVATE/'package-preflight-host-private.log').write_bytes(p.stdout+p.stderr)
(here/'package-preflight-validation.json').write_text(json.dumps(json.loads(p.stdout),indent=2)+'\n')
print(p.stdout.decode())
