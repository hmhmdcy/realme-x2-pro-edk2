import host

code='''from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai')
report=dict(sdk_directories=[p.name for p in root.iterdir() if p.is_dir() and 'sdk' in p.name],
 cached_apks={name:[p.name for p in (root/name).glob('*.apk')] for name in ['k148-sdk-apks','k184-libssc-deps-apks']},
 compiler_paths={cmd:subprocess.run(['sh','-c','command -v '+cmd],capture_output=True).stdout.decode().strip() for cmd in ['gcc','cc','meson','ninja','readelf','pkg-config']})
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'build-environment-private.json').write_bytes(p.stdout);print(p.stdout.decode())
