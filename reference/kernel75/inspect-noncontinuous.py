from pathlib import Path
import gzip, re, hashlib, json

out = Path('/mnt/e/edk2-samurai-out/kernel75')
raw = gzip.decompress((out/'noncontinuous-kms.gz').read_bytes())
(out/'noncontinuous-kms.txt').write_bytes(raw)
parts = re.split(r'(={5,}[^\n]+=+)', raw.decode())
for i in range(1, len(parts), 2):
    if re.search(r'dsi|phy', parts[i], re.I):
        print(parts[i], parts[i+1][:7000])
dmesg = gzip.decompress((out/'noncontinuous-dmesg.gz').read_bytes())
(out/'noncontinuous-dmesg.txt').write_bytes(dmesg)
lines = dmesg.decode().splitlines()
for line in lines:
    if re.search(r'DSC|power mode|DSI.*error|frame stalled|CTL|underflow|Oops|BUG:', line, re.I):
        print(line)
print('DSI error count:', sum('dsi_err_worker' in line for line in lines))
