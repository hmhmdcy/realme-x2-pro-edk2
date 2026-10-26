"""Finish the failed geometry check from frozen FV outputs; no rebuild or deployment."""
from pathlib import Path
import ast, hashlib, importlib.util, inspect, json, os, shutil, struct, subprocess, traceback

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual505_boot_pack',HERE/'package-boot.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
OUT=p.ROOT/'apsd-image505-boot-private-02'
assert not OUT.exists() and not (HERE/'boot-package-r2-result.json').exists()
old=p.check_local(); prior=json.loads((p.OUT/'result.json').read_bytes())
assert not prior['passed'] and prior['geometry_passed'] is False
assert 'Compressed result exceeds original absolute tail' in prior['error']
assert prior['parent_inputs_unchanged'] and prior['parent_mountinfo_unchanged']
for name,digest in prior['artifact_sha256'].items():
    assert p.file_sha(p.OUT/name)==digest,(name,'cached artifact changed')
assert p.sha((p.OUT/'raw.bin').read_bytes())=='32df8395abb630d51035c635eb999603668467c03a8a23a5ba4ec10362f12eeb'
paths=[p.CURRENT,p.EFI,p.DTB,p.PAIR,p.OUT/'raw.bin',p.OUT/'compact.fd',p.OUT/'main.Fv',p.OUT/'result.json',HERE/'package-boot.py',Path(__file__),Path('/usr/bin/gzip')]
before={str(q):p.file_sha(q) for q in paths}; mount=Path('/proc/self/mountinfo').read_bytes()
OUT.mkdir(); result=dict(passed=False,scope='recompress cached complete firmware only, same absolute tail',parent_inputs_before=before,first_geometry_failure_preserved=True)
try:
    gzpath=OUT/'raw-level9.gz'
    with (p.OUT/'raw.bin').open('rb') as source,gzpath.open('xb') as target,(OUT/'gzip.stderr').open('xb') as error:
        child=subprocess.run(['/usr/bin/gzip','-9','-c'],stdin=source,stdout=target,stderr=error,env={'PATH':'/usr/bin:/bin'})
        target.flush();os.fsync(target.fileno())
    assert child.returncode==0 and not (OUT/'gzip.stderr').read_bytes()
    gz=gzpath.read_bytes(); expected=bytearray(old['gzip'][:10]);expected[8]=2
    assert gz[:10]==expected and gz[3]==0
    import zlib
    assert zlib.decompress(gz,31)==(p.OUT/'raw.bin').read_bytes()
    # Only gzip's standard XFL compression-level hint differs from the prior header.
    source=inspect.getsource(p.decode_payload)
    original="assert gz[:10].hex() == m['android']['gzip_header_hex'] and gz[3] == 0"
    replacement="assert gz[:8] == bytes.fromhex(m['android']['gzip_header_hex'])[:8] and gz[8] in (0, 2) and gz[9] == bytes.fromhex(m['android']['gzip_header_hex'])[9] and gz[3] == 0"
    assert source.count(original)==1
    exec(compile(source.replace(original,replacement),str(__file__)+':standard-gzip-XFL','exec'),p.__dict__)
    payload=gz+old['compat'];ks=len(payload);new_ram=2048+p.align(ks,2048);used=new_ram+2048
    assert used<=p.LIMIT,(used,p.LIMIT)
    header=bytearray(old['header']);header[8:12]=struct.pack('<I',ks);header[576:608]=p.id_value(payload,b'\n')
    target=OUT/'boot-apsd505-private.img'
    with target.open('xb') as stream,p.CURRENT.open('rb') as original_file:
        stream.write(header);stream.write(payload);stream.write(bytes(new_ram-2048-ks));stream.write(old['ram_page'])
        assert stream.tell()==used
        original_file.seek(used);shutil.copyfileobj(original_file,stream,1024*1024);stream.flush();os.fsync(stream.fileno())
    assert target.stat().st_size==p.PARTITION
    parsed=p.unpack(target);assert parsed['raw']==(p.OUT/'raw.bin').read_bytes()
    assert parsed['fd']==(p.OUT/'compact.fd').read_bytes() and parsed['shim']==old['shim'] and parsed['compat']==old['compat']
    verification=p.verify_main(parsed['main'],old)
    a,b=p.raw_files(parsed['fd']),p.raw_files(old['fd'])
    assert a[p.SEC]['offset']==b[p.SEC]['offset']==0xfe8 and a[p.SEC]['full']==b[p.SEC]['full']
    assert a[p.CONTAINER]['offset']==b[p.CONTAINER]['offset']
    normalized=bytearray(parsed['header']);previous=bytearray(old['header'])
    for data in [normalized,previous]:data[8:12]=bytes(4);data[576:608]=bytes(32)
    assert normalized==previous and parsed['ram_page']==old['ram_page']
    assert p.equal_tail(target,p.CURRENT,used) and p.equal_tail(target,p.CURRENT,p.LIMIT)
    result.update(passed=True,boot_path=str(target),boot_sha256=p.file_sha(target),boot_bytes=p.PARTITION,new_kernel_size=ks,new_used=used,
        original_tail_start=p.LIMIT,absolute_tail_exact=True,compression_level=9,gzip_only_XFL_hint_changed=True,
        raw_firmware_exact_cached=True,main_verification=verification,SEC_complete_FFS_and_offset_exact=True,
        shim_compat_ramdisk_exact=True,header_only_size_ID_changed=True,written_boot_fully_reparsed=True,
        BDS_EFI_sha256=p.file_sha(p.EFI),native_DTB_sha256=p.file_sha(p.DTB),rollback_boot_sha256=p.file_sha(p.CURRENT),no_device_action=True)
except BaseException as error:result.update(error=repr(error),traceback=traceback.format_exc())
finally:
    after={str(q):p.file_sha(q) for q in paths};result.update(parent_inputs_after=after,parent_inputs_unchanged=before==after,parent_mountinfo_unchanged=mount==Path('/proc/self/mountinfo').read_bytes())
    result['passed']=result['passed'] and result['parent_inputs_unchanged'] and result['parent_mountinfo_unchanged']
    p.save(OUT/'result.json',result);p.save(HERE/'boot-package-r2-result.json',result)
    print(json.dumps({k:result.get(k) for k in ['passed','boot_sha256','new_used','error']}))
raise SystemExit(0 if result['passed'] else 1)
