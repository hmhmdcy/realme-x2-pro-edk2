from pathlib import Path
import hashlib,json,subprocess,tarfile,urllib.error,urllib.request
import host

out=host.PRIVATE/'upstream-apks';out.mkdir(mode=0o700,exist_ok=True)
# Metadata was captured before the interrupted large transfer. Fetching signed
# upstream archives is independent of recovering the native candidate transfer.
metadata=json.loads((host.PRIVATE/'installed-mm-metadata-private.json').read_text())
apk='/home/cy122/pmos-samurai-rootfs01/work/apk.static';keys='/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys'
records=[]
for item in metadata:
    if not item['P'].startswith('modemmanager'):continue
    filename=item['P']+'-'+item['V']+'.apk';destination=out/filename
    for repository in ['main','community']:
        url='https://dl-cdn.alpinelinux.org/alpine/edge/'+repository+'/aarch64/'+filename
        try:
            with urllib.request.urlopen(url,timeout=30) as response:data=response.read(30*1024*1024)
            break
        except urllib.error.HTTPError as error:
            if error.code!=404:raise
    else:raise RuntimeError('Pinned upstream package unavailable: '+filename)
    destination.write_bytes(data)
    verification=subprocess.run([apk,'--keys-dir',keys,'verify',str(destination)],capture_output=True,check=True)
    (host.PRIVATE/(item['P']+'-signature-verification.txt')).write_bytes(verification.stdout+verification.stderr)
    with tarfile.open(destination,'r:gz',ignore_zeros=True) as archive:
        raw=archive.extractfile('.PKGINFO').read().decode()
        controls={entry.name:archive.extractfile(entry).read().decode() for entry in archive.getmembers() if entry.isfile() and entry.name.startswith('.') and entry.name not in ['.PKGINFO'] and not entry.name.startswith('.SIGN')}
    fields={}
    for line in raw.splitlines():
        if ' = ' in line:
            name,value=line.split(' = ',1);fields.setdefault(name,[]).append(value)
    assert fields['pkgname']==[item['P']] and fields['pkgver']==[item['V']]
    assert fields['arch'] in ([['aarch64']] if item['P']=='modemmanager' else [['noarch'],['aarch64']])
    assert set(fields.get('depend',[]))==set(item.get('D','').split())
    (host.PRIVATE/(item['P']+'-upstream-pkginfo.txt')).write_text(raw)
    (host.PRIVATE/(item['P']+'-upstream-control-scripts.json')).write_text(json.dumps(controls,indent=2)+'\n')
    records.append(dict(name=item['P'],version=item['V'],arch=fields['arch'][0],url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),official_signature_verified=True,control_scripts=list(controls)))
(Path(__file__).resolve().parent/'upstream-package-validation.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records))
