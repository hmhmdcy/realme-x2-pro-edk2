import host,subprocess
code=b'''from pathlib import Path
out=Path('/var/lib/samurai/k190-mm-build')
for name in ['compile-resume']:
 p=out/(name+'-private.log')
 if p.exists():
  print(name,p.stat().st_size);print(p.read_text()[-1100:])
'''
try:p=host.ssh('python3 -',input=code)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/'inspect-build-failure-private.log').write_bytes(e.stdout+e.stderr);raise SystemExit('Private build inspection failed')
print(p.stdout.decode())
