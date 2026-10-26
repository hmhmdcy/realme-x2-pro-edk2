import host
code=b'''from pathlib import Path
import json,subprocess
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk')
lines=(out/'compile-resume-private.log').read_text().splitlines()
print('\\n'.join([x for x in lines if 'warning:' in x or 'not found' in x][:20]))
print('runtime_closure');print((out/'runtime-closure-private.txt').read_text()[:4500])
for name in ['libmount.so.1','libcap.so.2','libudev.so.1','libblkid.so.1','liblzma.so.5']:
 print(name,[(str(p),p.exists(),str(p.resolve())) for p in [Path('/lib')/name,Path('/usr/lib')/name,sdk/'usr/lib'/name]])
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
