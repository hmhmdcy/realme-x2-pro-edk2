from pathlib import Path
import hashlib,json,re
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
directory=json.loads((ref/'a11-directory-validation.json').read_text())
path=out/'a11-modem-bulk-private.bin'
assert path.stat().st_size==directory['bytes_to_read']
headers=(out/'a11-modem-bulk-headers-private.txt').read_text()
statuses=re.findall(r'^HTTP/\S+ (\d+)',headers,re.M)
ranges=re.findall(r'^content-range:\s*(.*?)\r?$',headers,re.I|re.M)
assert statuses[-1]=='206'
assert ranges[-1].strip()==f"bytes {directory['physical_bulk_start']}-{directory['physical_bulk_end']}/{directory['package_bytes']}"
report=dict(version=directory['version'],source_url=directory['url'],
    start=directory['physical_bulk_start'],end=directory['physical_bulk_end'],
    bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    exact_http_range_and_length_verified=True,zip_entry_crc_not_yet_verified=True,
    full_package_downloaded=False,phone_changed=False)
(ref/'a11-bulk-range-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
