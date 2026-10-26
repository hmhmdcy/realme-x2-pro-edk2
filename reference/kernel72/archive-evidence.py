from pathlib import Path
import gzip
import hashlib
import json
import re
import shutil

src = Path('/mnt/e/edk2-samurai-out/kernel72')
dest = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel72')
sha = lambda data: hashlib.sha256(data).hexdigest()
files = []
for p in sorted(src.iterdir()):
    if p.is_file() and (p.suffix in ('.txt','.json','.raw','.jsonl','.diff','.log','.out','.err','.gz','.sha256')
                       or p.name in ('config-before','config-ncm','init-before','init-after')):
        assert p.name not in ('id_ed25519','dropbear_ed25519_host_key')
        assert not re.search(rb'(?m)^-----BEGIN [A-Z ]*PRIVATE KEY-----$',p.read_bytes())
        shutil.copyfile(p, dest/p.name)
        files.append(p.name)
for name, compressed, expected, size in [
    ('usb-dmesg','usb-dmesg.gz','0e52718ab14c2892623a97c1a8cbb32895b37f7e1cfedd3aa0877158dde97cf0',91661),
    ('boot62-dmesg','boot62-dmesg.gz','d10761d7d2c0e4728b38cbf44d6d97e551df29b07b5a67fd1f2b74c1b0771ae7',53519),
    ('finish-dmesg','finish-dmesg.gz','be43829e3a55bfdda53835a12ba45d7bf84f83c8ef2c03d272aee8f985f02ebd',53594),
    ('finish-facts','finish-facts.gz','01fbbf7dfd66027ce3c519b2a687661f024abffcd494637302f9ad0eca8a6433',2285),
]:
    data = (dest/compressed).read_bytes()
    assert sha(data) == expected
    body = gzip.decompress(data)
    assert len(body) == size
    (dest/(name+'.validated.txt')).write_bytes(body)
    (dest/(name+'-validation.json')).write_text(json.dumps(dict(
        compressed_file=compressed,device_sha256=expected,plain_bytes=size,
        compressed_bytes=len(data),plain_sha256=sha(body),sha256_pass=True,
        gzip_crc_pass=True,length_pass=True),indent=2)+'\n')
traffic = []
for name, stage, direction, phone_file, phone_report in [
    ('download-test','before-flash','download','download-test','traffic-before-flash.txt'),
    ('upload-test','before-flash','upload','upload-test','traffic-before-flash.txt'),
    ('download-after-flash','after-flash','download','download-test','traffic-after-flash.txt'),
    ('upload-test','after-flash','upload','upload-test','traffic-after-flash.txt'),
]:
    text = (src/phone_report).read_text()
    expected = re.search(r'(?m)^([0-9a-f]{64})  /tmp/K72/'+phone_file+'$',text)[1]
    data = (src/name).read_bytes()
    assert len(data)==4194304 and sha(data)==expected
    traffic.append(dict(stage=stage,direction=direction,bytes=len(data),device_sha256=expected,
                        host_sha256=sha(data),sha256_pass=True,phone_report=phone_report,
                        original_retained_locally=True))
(dest/'traffic-validation.json').write_text(json.dumps(traffic,indent=2)+'\n')
private = dict(private_client_key_archived=False,private_host_key_archived=False,
               compiled_image_archived=False,dropbear_binary_archived=False,
               archived_files=files)
(dest/'archive-policy.json').write_text(json.dumps(private,indent=2)+'\n')
print(f'Archived {len(files)} public evidence files; verified 4 SCP exports and 4 traffic directions.')
