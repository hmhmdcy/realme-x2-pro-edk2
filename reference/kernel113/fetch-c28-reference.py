from pathlib import Path
import hashlib,json,sys,time,urllib.request,zipfile
variant=sys.argv[1] if len(sys.argv)>1 else 'c28'
assert variant in ('c28','c35')
asset={'c28':'Chinese_C28_firmware_only.zip','c35':'Global_C35_firmware_only.zip'}[variant]
out=Path('/mnt/e/edk2-samurai-out/kernel113')/(variant+'-reference-private')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
url='https://github.com/alextrack2013/rmx1931-stuff/releases/download/f14-2/'+asset
out.mkdir(exist_ok=True)
path=out/asset
if not path.exists():
    temporary=out/'download.partial'
    assert not temporary.exists(),'Inspect incomplete download before retrying'
    request=urllib.request.Request(url,headers={'User-Agent':'Realme-Samurai-Linux-Research'})
    total=0; deadline=time.monotonic()+180
    with urllib.request.urlopen(request,timeout=30) as response,temporary.open('xb') as dest:
        assert response.status==200
        while True:
            assert time.monotonic()<deadline,'Download deadline reached'
            block=response.read(1024*1024)
            if not block: break
            total+=len(block); assert total<=150*1024*1024,'Unexpected asset size'
            dest.write(block)
    temporary.replace(path)
with zipfile.ZipFile(path) as archive:
    bad=archive.testzip(); assert bad is None,bad
    entries=[dict(name=item.filename,bytes=item.file_size) for item in archive.infolist()]
    (out/'archive-inventory-private.json').write_text(json.dumps(entries,indent=2)+'\n')
    scripts=[i for i in archive.infolist() if i.filename.endswith('updater-script')]
    assert len(scripts)==1
    script=archive.read(scripts[0]).decode()
    (out/'updater-script-reference-private.txt').write_text(script)
    assert 'RMX1931' in script,'Missing intended device assertion'
    images=[i for i in entries if Path(i['name']).name in ('NON-HLOS.bin','modem.img')]
    assert len(images)==1,images
report=dict(source_url=url,package_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            package_bytes=path.stat().st_size,zip_crc_verified=True,
            updater_device_assertion_contains_rmx1931=True,modem_candidates=images,
            package_scripts_executed=False,package_flashed=False,
            source_is_maintainer_repack_not_official_download=True)
(ref/(variant+'-reference-download.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
