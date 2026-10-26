"""Reuse the frozen decoder/converter for one fixed new host system image."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,traceback,zipfile
ROOT=Path('E:/RealmeX2Pro edk2')
PRIVATE=Path('E:/edk2-samurai-out/charging-oem-audit-20261023')
HELPER=ROOT/'reference/charging-oem-audit-20261023/gauge-2719-vendor-extract-candidate/extract-vendor.py'
NODE_SCRIPT=HELPER.with_name('brotli-stream.js')
PLAN=PRIVATE/'gauge-2719-vendor-extract-plan-01/plan-private.json'
INPUT=PRIVATE/'gauge-2719-system-input-private-01/result-private.json'
OUT=PRIVATE/'gauge-2719-system-extract-private-01'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert not OUT.exists()
assert sha(HELPER.read_bytes())=='1cb0061483e7cc9a60f1c698110ef0d93930f11d5a87ae9b6224a10f22262555'
assert sha(NODE_SCRIPT.read_bytes())=='fbbd9edf189c1712b345a9e6fb1efe0bd917d6070335fead41e4e44278108c37'
spec=importlib.util.spec_from_file_location('reviewed_vendor_extract',HELPER)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
plan=json.loads(PLAN.read_bytes());source=Path(plan['source_zip']);node=Path(plan['node'])
assert source.is_file() and not source.is_symlink() and source.stat().st_size==3666753073
assert helper.digest(node)=='d702daa815eabbff763c7d3808e235cf031cf2ca70211b56847bc72f51e240e5'
input_result=json.loads(INPUT.read_bytes())
assert input_result['passed'] and input_result['system_new_bytes']==4219551744 and input_result['system_extent_bytes']==4487905280
def inspect():
    with zipfile.ZipFile(source) as z:
        infos=z.infolist();assert len(infos)==72 and len({i.filename for i in infos})==72
        info=z.getinfo('system.new.dat.br')
        assert (info.file_size,info.compress_size,info.compress_type,info.CRC,info.flag_bits)==(2196143558,2196143558,0,0x1d70832f,2048)
        assert z.getinfo('system.transfer.list').file_size==21442
        raw=z.read('system.transfer.list')
        assert sha(raw)=='c7d9077a08efd863730dea41237dcdd3fb4b2bbb0c17e7c878a99308e37df070'
        assert sha(z.read('META-INF/com/android/metadata'))=='3e005ffe4beaf27b2611052d9000ed2d700ded5607433e04c44bd987be8953c0'
    parsed=helper.parse_transfer(raw,4487905280)
    assert parsed['new_bytes']==4219551744 and parsed['counts']=={'erase':1,'new':1007,'zero':18}
    return raw,parsed
transfer,parsed=inspect();assert shutil.disk_usage(OUT.parent).free>12*1024**3
before=helper.stamp(source);self_sha=helper.digest(__file__)
OUT.mkdir(mode=0o700)
result=dict(passed=False,original_parent_pid=os.getpid(),scope='offline fixed system member only',source_before=before,
 source_helper_sha256=helper.digest(HELPER),node_script_sha256=helper.digest(NODE_SCRIPT),wrapper_sha256=self_sha,
 input_result_sha256=helper.digest(INPUT),expected_new_bytes=4219551744,expected_extent_bytes=4487905280)
try:
    (OUT/'system.transfer.list').write_bytes(transfer)
    result['compressed']=helper.copy_member(source,'system.new.dat.br',OUT/'system.new.dat.br',2196143558,0x1d70832f)
    helper.save(OUT/'result-private.json',result)
    print(json.dumps(dict(stage='compressed-member-CRC-and-EOF-verified',bytes=result['compressed']['bytes'])),flush=True)
    argv=[str(node),str(NODE_SCRIPT),str(OUT/'system.new.dat.br'),str(OUT/'system.new.dat'),'2196143558','4219551744',result['compressed']['sha256']]
    result['node_command']=dict(argv=argv,terminal=False)
    with (OUT/'node-stdout-private.json').open('xb') as out,(OUT/'node-stderr-private.log').open('xb') as err:
        child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
        result['node_command']['pid']=child.pid;helper.save(OUT/'result-private.json',result)
        print(json.dumps(dict(stage='brotli',original_node_pid=child.pid)),flush=True)
        try:child.wait()
        finally:child.wait();result['node_command'].update(terminal=True,returncode=child.returncode)
        out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
    assert child.returncode==0
    decoded=json.loads((OUT/'node-stdout-private.json').read_bytes())
    assert decoded['passed'] and decoded['input_complete'] and decoded['input_sha256']==result['compressed']['sha256']
    assert decoded['input_bytes']==decoded['engine_bytes_written']==2196143558
    assert decoded['output_forwarded_bytes']==decoded['output_file_bytes']==4219551744
    result['decoded']=decoded;helper.save(OUT/'result-private.json',result)
    print(json.dumps(dict(stage='decoded-EOF-verified',bytes=decoded['output_file_bytes'])),flush=True)
    result['image']=helper.rebuild_image(OUT/'system.new.dat',OUT/'system.img',parsed,decoded['output_sha256'])
    inspect();result['small_members_rechecked']=True;result['passed']=True
except BaseException as error:
    result.update(passed=False,error=repr(error),traceback=traceback.format_exc())
finally:
    result['source_after']=helper.stamp(source)
    result['source_stat_unchanged']=before==result['source_after']
    result['tools_and_sources_unchanged']=(helper.digest(__file__)==self_sha and helper.digest(HELPER)==result['source_helper_sha256']
        and helper.digest(NODE_SCRIPT)==result['node_script_sha256'] and helper.digest(node)=='d702daa815eabbff763c7d3808e235cf031cf2ca70211b56847bc72f51e240e5')
    result['passed'] &= result['source_stat_unchanged'] and result['tools_and_sources_unchanged']
    result.update(whole_OTA_SHA_or_signature_verified=False,filesystem_or_pack_verified=False,device_SDK_mount_or_Git_action=False)
    helper.save(OUT/'result-private.json',result)
    print(json.dumps(dict(passed=result['passed'],private_result_sha256=helper.digest(OUT/'result-private.json'),image=result.get('image'))),flush=True)
raise SystemExit(0 if result['passed'] else 1)
