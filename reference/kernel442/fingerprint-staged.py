from pathlib import Path
import json,shlex,sys
import host
HERE=Path(__file__).resolve().parent
attempts=sys.argv[1:];assert attempts and all(a.startswith('r') and a[1:].isdigit() for a in attempts)
code='''from pathlib import Path
import json
rows={}
for a in ATTEMPTS:
 r=Path('/var/lib/samurai/k442-callback-timing-'+a);m=json.loads((r/'manifest.json').read_text())
 rows[a]=dict(core_sha256=m['lib/libcamera.so.0.7.2'],capture_sha256=m['capture'],ipa_sha256=m['ipa/ipa_camss_vfe.so'])
print(json.dumps(rows))
'''.replace('ATTEMPTS',repr(attempts))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode()
for a,row in json.loads(q.stdout).items():
 p=HERE/f'runtime-staging-{a}-validation.json';d=json.loads(p.read_text());d.update(row);p.write_text(json.dumps(d,indent=2)+'\n')
print('Verified staged core/probe/IPA fingerprints for '+', '.join(attempts))
