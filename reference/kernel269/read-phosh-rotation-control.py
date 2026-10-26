"""Read matching upstream desktop controls before using their observed UI action."""
from pathlib import Path
import urllib.request
P=Path('/mnt/e/edk2-samurai-out/kernel269')
for name in ['quick-settings.c','rotation-info.c','quick-settings/rotation-quick-setting.c']:
 url='https://gitlab.gnome.org/World/Phosh/phosh/-/raw/v0.57.0/src/'+name
 try:
  raw=urllib.request.urlopen(url,timeout=15).read();(P/('phosh-'+name.replace('/','-'))).write_bytes(raw)
 except Exception as e:print(name,type(e).__name__);continue
 lines=raw.decode().splitlines();selected=set()
 for i,line in enumerate(lines):
  if any(s in line for s in ['rotation','MODE_SENSOR']):selected.update(range(max(0,i-2),min(len(lines),i+7)))
 print(name)
 for i in sorted(selected):print(str(i+1)+': '+lines[i])
