from pathlib import Path
import host,json,subprocess,time

ref=Path(__file__).resolve().parent
try:p=host.ssh('python3 -',input=(ref/'collect-newboot.py').read_bytes(),timeout=100)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'newboot-connect-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise SystemExit('New boot probe stopped; inspect private evidence, do not repeat a transition')
(host.PRIVATE/'runtime-private.json').write_bytes(p.stdout)
r=json.loads(p.stdout);assert r['new_boot_identity_verified']
(ref/'runtime-validation.json').write_text(json.dumps(r,indent=2)+'\n')
host.download('/var/lib/samurai/k200-runtime/boot-id-private.txt',host.PRIVATE/'new-boot-id-private.txt')
print(json.dumps(r))
