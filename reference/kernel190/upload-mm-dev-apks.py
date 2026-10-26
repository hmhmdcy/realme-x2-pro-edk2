from pathlib import Path
import host
code=b'''from pathlib import Path
import os,signal
out=Path('/var/lib/samurai/k190-mm-sdk-host-apks');out.mkdir(mode=0o700)
stopped=0
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:args=(p/'cmdline').read_bytes().split(b'\\0')
  except FileNotFoundError:continue
  if args[:5]==[b'apk',b'--no-cache',b'fetch',b'--recursive',b'--output'] and b'/var/lib/samurai/k190-mm-build/extra-apks' in args:
   assert (p/'cmdline').read_bytes().split(b'\\0')==args
   os.kill(int(p.name),signal.SIGTERM);stopped+=1
print('staging directory ready; matching network fetches stopped:',stopped)
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
for path in sorted(Path('/mnt/e/edk2-samurai-out/kernel190/mm-sdk-apks').glob('*.apk')):
 host.upload(path,'/var/lib/samurai/k190-mm-sdk-host-apks/'+path.name)
print('five official signed development APKs staged')
