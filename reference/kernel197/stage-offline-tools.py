from pathlib import Path
import hashlib,json,host
out=host.PRIVATE;manifest=json.loads((out/'video-package-download-private.json').read_text());records=[]
for name in ['v4l-utils-libs-1.32.0-r1.apk','v4l-utils-1.32.0-r1.apk','front-capture-aarch64-private']:
 p=out/name;assert p.is_file();records.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
build=json.loads((Path(__file__).resolve().parent/'capture-tool-build-validation.json').read_text());assert records[-1]['sha256']==build['static_binaries'][1]['sha256']
host.ssh('python3 -',input=b"from pathlib import Path\nimport os\nos.umask(0o077)\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k197-baseline/boot-id-private.txt').read_bytes()\nPath('/var/lib/samurai/k197-offline-tools').mkdir(mode=0o700)\n",timeout=20)
for r in records:host.upload(out/r['file'],'/var/lib/samurai/k197-offline-tools/'+r['file'])
(out/'offline-tools-manifest-private.json').write_text(json.dumps(records,indent=2)+'\n');host.upload(out/'offline-tools-manifest-private.json','/var/lib/samurai/k197-offline-tools/manifest.json');print('Verified tool files staged')
