from pathlib import Path
import hashlib,json,lzma,struct,sys,zlib

ref=Path('/mnt/e/RealmeX2Pro edk2/reference')
helpers=(ref/'kernel104/verify-firmware.py').read_text().split('dt_audit=')[0]
ns={}
exec(compile(helpers,'firmware-format-helpers','exec'),ns)
fv,sections,align=ns['fv'],ns['sections'],ns['align']
dt_guid,lz_guid,cmd=ns['dt_guid'],ns['lz_guid'],ns['cmd']
base_out=Path('/mnt/e/edk2-samurai-out/kernel113')
out=base_out/'canonical-firmware' if '--canonical' in sys.argv else base_out
sha=lambda b:hashlib.sha256(b).hexdigest()
data={}
for tag,filename in [('before','boot-before.img'),('after','boot-k113-sensors.img')]:
    boot=(out/filename).read_bytes()
    fd=(out/f'firmware-{tag}.fd').read_bytes()
    main=(out/f'fvmain-{tag}.Fv').read_bytes()
    compact=(out/f'fvcompact-{tag}.Fv').read_bytes()
    dtb=(out/f'firmware-{tag}.dtb').read_bytes()
    compat=(out/'compat-before.dtb').read_bytes()
    assert boot[:8]==b'ANDROID!'
    ks,rs,ss,pg,version=[struct.unpack_from('<I',boot,o)[0] for o in (8,16,24,36,40)]
    assert version==1 and pg==2048 and rs==1 and ss==0
    assert len(boot)==pg+align(ks,pg)+align(rs,pg)
    decoder=zlib.decompressobj(31)
    raw=decoder.decompress(boot[pg:pg+ks])+decoder.flush()
    assert decoder.eof and decoder.unused_data==compat and not decoder.unconsumed_tail
    assert raw[144:]==fd and fd==compact and len(fd)==0x700000
    modules=fv(main);compact_modules=fv(compact)
    dt=modules[dt_guid]['sections']
    assert len(dt)==1 and dt[0][0]==0x19 and dt[0][1]==dtb
    images=[m for m in compact_modules.values() if m['type']==0xb]
    assert len(images)==1 and len(images[0]['sections'])==1
    typ,body,section=images[0]['sections'][0]
    import uuid
    assert typ==2 and str(uuid.UUID(bytes_le=body[:16]))==lz_guid
    offset,attrs=struct.unpack_from('<HH',body,16)
    nested=sections(lzma.decompress(section[offset:],format=lzma.FORMAT_ALONE))
    assert len(nested)==1 and nested[0][0]==0x17 and nested[0][1]==main
    assert cmd.encode('utf-16-le') in main
    assert 'Linux (mainline samurai)'.encode('utf-16-le') in main
    data[tag]=dict(boot=boot,shim=raw[:144],modules=modules,compact_modules=compact_modules,
                   ramdisk=boot[pg+align(ks,pg):pg+align(ks,pg)+rs],page=pg)
old,new=data['before'],data['after']
assert old['shim']==new['shim'] and old['ramdisk']==new['ramdisk']
headers=[bytearray(d['boot'][:d['page']]) for d in (old,new)]
for h in headers:h[8:12]=b'\0'*4;h[576:608]=b'\0'*32
assert headers[0]==headers[1]
assert old['modules'].keys()==new['modules'].keys()
changes=[]
for guid,m in old['modules'].items():
    n=new['modules'][guid]
    assert (m['type'],m['attrs'])==(n['type'],n['attrs'])
    if m['body']!=n['body']:
        changes.append(dict(guid=guid,name=n['name'],before_sha256=sha(m['body']),after_sha256=sha(n['body'])))
(out/'firmware-module-differences-private.json').write_text(json.dumps(changes,indent=2)+'\n')
assert len(changes)==1 and changes[0]['guid']==dt_guid, 'Unexpected executable/module bytes changed; candidate must not be deployed'
assert old['compact_modules'].keys()==new['compact_modules'].keys()
for guid,m in old['compact_modules'].items():
    n=new['compact_modules'][guid]
    if m['body']!=n['body']:assert m['type']==0xb
active=(Path('/mnt/e/edk2-samurai-out/kernel109')/'boot-partition-before.img').read_bytes()
assert active[:len(old['boot'])]==old['boot']
assert (out/'firmware-after.dtb').read_bytes()==(base_out/'dtb-sensor-power').read_bytes()
original=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb')
assert original.read_bytes()==(base_out/'dtb-before').read_bytes()
actual_before=(base_out/'boot-partition-before.img').read_bytes()
prior=base_out.parent/'kernel111/canonical-firmware'
prior_boot=(prior/'boot-k111-sensors.img').read_bytes()
assert actual_before[:len(prior_boot)]==prior_boot
prior_modules=fv((prior/'fvmain-after.Fv').read_bytes())
assert prior_modules.keys()==new['modules'].keys()
for guid,m in prior_modules.items():
    n=new['modules'][guid]
    assert (m['type'],m['attrs'])==(n['type'],n['attrs'])
    if guid!=dt_guid: assert m['body']==n['body']
report=dict(firmware_audit_pass=True,bootshim_preserved=True,other_executable_bytes_unchanged=True,
            actual_device_boot_111_executables_preserved=True,
            canonical_baseline_boot_matches_109=True,only_embedded_dtb_changed=True,
            original_firmware_source_preserved=True,boot_bytes=len(new['boot']),
            boot_sha256=sha(new['boot']),dtb_sha256=sha((base_out/'dtb-sensor-power').read_bytes()),
            android_header_preserved=True,compat_append_preserved=True,
            gzip_crc_fv_ffs_checksums_and_compact_lzma_pass=True)
(out/'firmware-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
