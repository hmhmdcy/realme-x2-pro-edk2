from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess,urllib.request,urllib.error

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
repo=out/'realme-updates-tracker-reference-private'
revision='6e0a3181b7c365b5a9d560c9abe164100b9faec3'
payload=subprocess.check_output(['git','-C',str(repo),'show',revision+':data/archive/RMX1931.yml'])
links={}
for line in payload.decode().splitlines():
    if ': https://' in line:
        name,url=line.strip().split(': ',1)
        if name in ('RMX1931_11.A.11','RMX1931_11.A.13','RMX1931_11.A.15'):
            assert url.startswith('https://download.c.realme.com/osupdate/RMX1931_11_OTA_')
            links[name]=url
assert len(links)==3

def probe(item):
    name,url=item
    result=dict(version=name,url=url,full_package_downloaded=False,phone_changed=False)
    try:
        request=urllib.request.Request(url,headers={'Range':'bytes=0-1023','User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=20) as response:
            # An ignored Range must still never become a multi-GB download.
            header=response.read(1024)
            result.update(http_status=response.status,bytes_read=len(header),
                content_length=response.headers.get('Content-Length'),
                content_range=response.headers.get('Content-Range'),
                content_type=response.headers.get('Content-Type'),
                final_url=response.url,header_sha256=hashlib.sha256(header).hexdigest(),
                oppo_encryption_magic=header.startswith(b'OPPOENCRYPT!'))
            (out/(name.replace('.','-')+'-header-private.bin')).write_bytes(header)
    except urllib.error.HTTPError as error:
        result.update(http_status=error.code,bytes_read=0,error_type=type(error).__name__)
    except Exception as error:
        result.update(bytes_read=0,error_type=type(error).__name__)
    return result

with ThreadPoolExecutor(max_workers=3) as executor:
    results=list(executor.map(probe,links.items()))
report=dict(source='https://github.com/RealmeUpdater/realme-updates-tracker',
    archive_revision=revision,archive_sha256=hashlib.sha256(payload).hexdigest(),
    probes=results,slpi_version_not_yet_verified=True,
    firmware_candidate_not_yet_extracted=True,phone_changed=False)
(ref/'older-realme-package-links.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
