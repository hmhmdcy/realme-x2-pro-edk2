from pathlib import Path
import hashlib,json,re
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
directory=json.loads((ref/'a11-directory-validation.json').read_text())
initial=out/'a11-modem-bulk-private.bin'
assert initial.stat().st_size==21011704<directory['bytes_to_read']
tail=out/'a11-modem-bulk-tail-private.bin'
assert not tail.exists() or tail.stat().st_size==0
headers=(out/'a11-modem-bulk-headers-private.txt').read_text()
expected=f"bytes {directory['physical_bulk_start']}-{directory['physical_bulk_end']}/{directory['package_bytes']}"
assert re.findall(r'^content-range:\s*(.*?)\r?$',headers,re.I|re.M)[-1].strip()==expected
cached=[]
for path in sorted((out/'a11-range-cache-private').glob('*.bin')):
    match=re.fullmatch(r'(\d+)-(\d+)\.bin',path.name)
    assert match and path.stat().st_size==int(match[2])-int(match[1])+1
    cached.append(dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
assert not (ref/'a11-package-range-validation.json').exists()
assert not (out/'a11-reference-private/modem.img').exists()
report=dict(version=directory['version'],source_url=directory['url'],
    zip_directory_read=True,zip_directory_entries=68,selected_entry=directory['selected_entry'],
    selected_entry_zip_crc32=directory['zip_crc32'],selected_entry_compressed_bytes=directory['compressed_bytes'],
    selected_entry_crc_verified=False,complete_modem_extracted=False,slpi_extracted=False,
    partial_bulk_bytes=initial.stat().st_size,
    partial_bulk_sha256=hashlib.sha256(initial.read_bytes()).hexdigest(),
    initial_curl_timeout_exit=28,tail_curl_incomplete_response_exit=18,
    accepted_transport_length_cache_files=len(cached),
    incomplete_downloads_preserved_privately=True,linux_deployed=False,
    original_phone_configuration_changed=False,goal_complete=False)
(out/'a11-cache-inventory-private.json').write_text(json.dumps(cached,indent=2)+'\n')
(ref/'a11-reference-attempt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
