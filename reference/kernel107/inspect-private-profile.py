from pathlib import Path
import collections,re
s=Path('/mnt/e/edk2-samurai-out/kernel107/wpa-5g-private.conf').read_text()
print('PROFILE_KEYS',dict(collections.Counter(re.findall(r'^\s*([a-z_]+)\s*=',s,re.M))))
for k in ['scan_freq','freq_list']:
    m=re.search(r'^\s*'+k+r'\s*=\s*([0-9 ]+)\s*$',s,re.M)
    print(k,m[1] if m else 'ABSENT')
