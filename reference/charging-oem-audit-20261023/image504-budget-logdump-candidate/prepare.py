"""Text-derive the bounded FAT method; never imports old generators or runs tools."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
METHOD=REF/'charging-session-20261023/gauge-image502-logdump-candidate'
IMAGE_LEAF=HERE.parent/'dwc-image504-budget-fence-candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(METHOD/'delivery.json')=='eb615331fcb75fbb4cfb21064cea5a8effeffe386ad5ce8839989c7c359420ce'
method=json.loads((METHOD/'delivery.json').read_bytes())
for name,pin in method['files'].items():assert sha(METHOD/name)==pin,name
assert sha(METHOD/'package-logdump.py')=='1a262316bc43536dcbc0c4305114deff31b9bcb13850e3674829f74ad6ac01e6'
assert sha(IMAGE_LEAF/'delivery.json')=='88aa96af5b451c7778503f89b549f8d7abd131bd8cf330c87368e7552147b482'
delivery=json.loads((IMAGE_LEAF/'delivery.json').read_bytes())
for name,row in delivery['files'].items():assert sha(IMAGE_LEAF/name)==row['sha256'],name
pins=dict(ready=True,actual_completed_build=True,delivery_sha256=sha(IMAGE_LEAF/'delivery.json'),
    receipts={n:sha(IMAGE_LEAF/n) for n in ['build-result.json','abi-reuse-result.json','execution-receipt.json','owner-result.json']},
    Image_sha256=delivery['outputs']['arch/arm64/boot/Image']['sha256'],Image_bytes=delivery['outputs']['arch/arm64/boot/Image']['bytes'],
    DWC_sources=delivery['source_changes'],paired_provider_module_sha256='2691c3ceb6245c7c4999c122f015ad93588dce5928b8cd982a5ac725539c4448',
    provider_installed_or_cohort_bound=False,actual_phone_502_adoption_claimed=False)
(HERE/'Image504-pins.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf-8',newline='\n')
old=(METHOD/'package-logdump.py').read_text();text=old
def sub(a,b):
    global text
    assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b,1)
sub('Only privately replace current Image501 FAT /Image with frozen Image502.',
    'Only replace saved candidate502 FAT /Image with actual504; no live identity or deployment.')
sub("OLD=ROOT/'charging-management-20261023/gauge-image501-logdump-private-01/logdump-gauge501-private.img'",
    "OLD=ROOT/'charging-management-20261023/gauge-image502-logdump-private-01/logdump-gauge502-private.img'")
sub("IMAGE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01/build/arch/arm64/boot/Image')",
    "IMAGE=Path('/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01/build/arch/arm64/boot/Image')")
sub("OUT=ROOT/'charging-management-20261023/gauge-image502-logdump-private-01'",
    "OUT=ROOT/'charging-management-20261023/image504-budget-logdump-private-01'")
start=text.index('def load_502_proof():');end=text.index('def check_local():',start)
text=text[:start]+(HERE/'proof-gate.inc').read_text()+'\n'+text[end:]
sub("    old=pinned(OLD,'7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9')",
    "    check_502_carrier_proof()\n    old=pinned(OLD,'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1')")
sub("    assert f['files']['Image']['sha256']=='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'",
    "    assert f['files']['Image']['sha256']=='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'")
sub('proof=load_502_proof()', 'proof=load_504_proof()')
sub("Image502 frozen terminal proof not supplied", "Image504 completed-build proof not supplied")
start=text.index('    paths=[OLD,IMAGE,Path(__file__)');end=text.index('\n    before=',start)
text=text[:start]+'''    paths=[OLD,IMAGE,Path(__file__),HERE/'Image504-pins.json']
    paths += [HERE.parents[1]/'charging-oem-audit-20261023/dwc-image504-budget-fence-candidate'/n for n in
              ['delivery.json','build-result.json','abi-reuse-result.json','execution-receipt.json','owner-result.json']]
    paths += [HERE.parents[1]/'charging-session-20261023/gauge-image502-logdump-candidate'/n for n in ['delivery.json','logdump-result.json']]
    paths += [Path(p) for p,_ in TOOLS.values()]'''+text[end:]
sub("target=OUT/'logdump-gauge502-private.img'", "target=OUT/'logdump-image504-private.img'")
sub('private undeployed current-501 FAT Image502 replacement only','private undeployed saved-candidate502 FAT Image504 replacement only')
sub("'Image502_sha256':sha(image)","'Image504_sha256':sha(image)")
sub("'Image502_proof_ready'", "'Image504_proof_ready'")
start=text.index('    def run(name,args,stage):');end=text.index('\n    try:',start)
text=text[:start]+'''    def run(name,args,stage):
        argv=[TOOLS[name][0]]+list(map(str,args));e={'stage':stage,'argv':argv};r['commands'].append(e);save(OUT/'result.json',r)
        with (OUT/(stage+'.stdout')).open('wb') as out,(OUT/(stage+'.stderr')).open('wb') as err:
            q=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=dict(os.environ,PATH='/usr/bin:/bin',MTOOLS_SKIP_CHECK='0'))
            try:
                e.update(pid=q.pid,terminal=False);save(OUT/'result.json',r)
                print(json.dumps({'stage':stage,'pid':q.pid,'started':True}),flush=True)
            finally:
                rc=q.wait()
                e.update(terminal=True,returncode=rc)
            out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
        save(OUT/'result.json',r);assert rc==0,stage+' failed'
'''+text[end:]
sub("    except BaseException as exc:r['error']=repr(exc);r['traceback']=traceback.format_exc()",
    "    except BaseException as exc:\n        r['passed']=False;r['error']=repr(exc);r['traceback']=traceback.format_exc()")
sub('                 rootfs_R8_camera_untouched=True,no_device_or_deployment=True)',
    '''                 rootfs_R8_camera_untouched=True,no_device_or_deployment=True,
                 candidate={'path':str(target),'sha256':sha(new),'bytes':len(new)},
                 rollback={'path':str(OLD),'sha256':sha(old),'bytes':len(old)},
                 Image504={'sha256':sha(image),'bytes':len(image)},
                 actual_phone_502_adoption_claimed=False)''')
ast.parse(text)
(HERE/'package-logdump.py').write_text(text,encoding='utf-8',newline='\n')
(HERE/'method-delta.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),
    fromfile='frozen502/package-logdump.py',tofile='image504/package-logdump.py')),encoding='utf-8',newline='\n')
def fn(s,n):
    node=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name==n)
    return '\n'.join(s.splitlines()[node.lineno-1:node.end_lineno])
for name in ['read_bytes','parse_fat','pinned']:assert fn(old,name)==fn(text,name),name
range_start='        # Require all changed bytes';range_end='        r.update(passed=True'
assert old[old.index(range_start):old.index(range_end)]==text[text.index(range_start):text.index(range_end)]
assert 'subprocess.run(' not in text and 'timeout=' not in text
reuse=dict(passed=True,method_delivery_sha256=sha(METHOD/'delivery.json'),method_package_sha256=sha(METHOD/'package-logdump.py'),
    candidate_package_sha256=sha(HERE/'package-logdump.py'),actual504_delivery_sha256=sha(IMAGE_LEAF/'delivery.json'),
    unchanged_functions_LF_text={n:hashlib.sha256(fn(text,n).encode()).hexdigest() for n in ['read_bytes','parse_fat','pinned']},
    ranges_and_fsck_sequence_LF_text_identical=True,bounded_read_chunk_bytes=1048576,
    raw_source_files_pinned_separately=True,no_old_generator_imported=True,
    same_original_Popen_finally_wait_no_timeout=True,except_forces_passed_false=True,
    rollback_saved502_sha256='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1',
    private_OUT_created=False,new_Image_or_FAT_read_by_generator=False,tool_or_device_or_storage_invoked=False)
(HERE/'reuse-result.json').write_text(json.dumps(reuse,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(reuse))
