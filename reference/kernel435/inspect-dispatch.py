from pathlib import Path
import storage
T=storage.candidate()/'src/libcamera-v0.7.2'
for p in (T/'output').rglob('*camss*'):
 if p.suffix not in ['.cpp','.h']:continue
 lines=p.read_text().splitlines()
 if not any('processStats(' in l for l in lines):continue
 print(p.name)
 for i,line in enumerate(lines):
  if ('invokeMethod' in line or 'prepareIpeParameters(' in line or 'void IPAProxyCamss::processStats(' in line):
   print('\n'.join(lines[max(0,i-2):min(len(lines),i+8)]))
