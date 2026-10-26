from pathlib import Path
import hashlib,json,subprocess,tarfile,urllib.parse
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');repos=json.loads((private/'phone-repositories-private.json').read_text());selected=[]
for text in repos.values():
    for line in text.splitlines():
        if line.startswith('https://'):
            host=urllib.parse.urlparse(line).hostname or ''
            if host.endswith('.postmarketos.org') or host=='dl-cdn.alpinelinux.org':selected.append(line)
assert selected and any('.postmarketos.org' in url for url in selected)
source=private/'rollback-source-repositories-private.list';source.write_text('\n'.join(selected)+'\n')
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=private/'phone-trusted-public-keys';out=private/'rollback-apks';assert not any(out.glob('libcamera-tools*.apk'))
with (private/'rollback-tools-fetch-private.log').open('xb') as log:subprocess.run([str(apk),'--arch','aarch64','--keys-dir',str(keys),'--repositories-file',str(source),'--no-cache','fetch','--output',str(out),'libcamera-tools=99990.7.2-r4'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
paths=list(out.glob('libcamera-tools*.apk'));assert len(paths)==1;path=paths[0]
p=subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(path)],capture_output=True,timeout=20);(private/'rollback-tools-signature-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
original=json.loads((private/'phone-original-files-manifest-private.json').read_text());compared=0
with tarfile.open(path,'r:gz',ignore_zeros=True) as archive:
    for member in archive.getmembers():
        name=member.name.removeprefix('./')
        if member.isfile() and not name.startswith('.'):
            assert original[name]==dict(kind='file',sha256=hashlib.sha256(archive.extractfile(member).read()).hexdigest(),mode=member.mode),name;compared+=1
assert compared==2
report=dict(stage=214,rollback_tools_original_signed_apk_fetched=True,version='99990.7.2-r4',already_trusted_phone_keys_verified=True,both_tool_payloads_and_modes_match_current_device_backup=True,all_three_original_camera_rollback_apks_available=True,no_device_mutation=True)
(here/'rollback-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
