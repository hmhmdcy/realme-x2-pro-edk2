"""Accept the original baseline warnings; convert the completed DLL once."""
from pathlib import Path
import hashlib,json,os,re,struct,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];HANDOFF=HERE.parent/'eud-route-handoff-candidate'
OUT=Path('/home/cy122/charging-management-20261023/apsd-image505-bds-01');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((HERE/'dtb-and-command-r2-result.json').read_bytes());previous=json.loads((HANDOFF/'build-result.json').read_bytes())
recipes=json.loads((REF/'charging-session-20261023/eud-bds-r2-build/result.json').read_bytes())
commands=json.loads((OUT/'commands-private.json').read_bytes());assert [row['name'] for row in commands]==['compile-BDS','archive-one-object','link-BDS-DXE']
assert all(row['terminal'] and row['returncode']==0 for row in commands)
assert sha(OUT/'PlatformBm.c')==proof['BDS_source_sha256']==sha(HERE/'PlatformBm.c.candidate')
def normalize(raw):
 text=re.sub(r'using serial compilation of [0-9]+ LTRANS jobs','using serial compilation of N LTRANS jobs',raw.decode())
 return re.sub(r'warning: [^\n]+/BdsDxe.dll has a LOAD segment','warning: BdsDxe.dll has a LOAD segment',text)
baseline=Path(recipes['private_directory'])/'link.stderr';observed=OUT/'link-BDS-DXE.stderr'
assert normalize(baseline.read_bytes())==normalize(observed.read_bytes())
assert not (OUT/'BdsDxe.efi').exists()
intent=dict(DLL_sha256=sha(OUT/'BdsDxe.dll'),source_sha256=sha(OUT/'PlatformBm.c'),original_link_terminal0=True,normalized_warnings_equal_original_passed_R2=True)
with (OUT/'finish-intent-private.json').open('x') as stream:json.dump(intent,stream,indent=2);stream.write('\n')
argv=list(next(row['argv'] for row in recipes['child']['commands'] if row['stage']=='GenFw'));argv[argv.index('-o')+1]=str(OUT/'BdsDxe.efi');argv[-1]=str(OUT/'BdsDxe.dll')
child=subprocess.Popen(argv,cwd=OUT,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
stdout,stderr=child.communicate();child.wait();(OUT/'GenFw.stdout').write_bytes(stdout);(OUT/'GenFw.stderr').write_bytes(stderr)
row=dict(name='GenFw',pid=child.pid,terminal=True,returncode=child.returncode,argv=argv,diagnostic_bytes=len(stderr))
(OUT/'finish-terminal-private.json').write_text(json.dumps(row,indent=2)+'\n');assert child.returncode==0 and not stderr
efi=(OUT/'BdsDxe.efi').read_bytes();assert efi[:2]==b'MZ';pe=struct.unpack_from('<I',efi,0x3c)[0]
assert efi[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',efi,pe+4)[0]==0xaa64 and struct.unpack_from('<H',efi,pe+24)[0]==0x20b
assert struct.unpack_from('<H',efi,pe+24+68)[0]==11 and proof['candidate_cmdline'].encode('utf-16-le') in efi
def sections(raw):
 pe=struct.unpack_from('<I',raw,0x3c)[0];count=struct.unpack_from('<H',raw,pe+6)[0];size=struct.unpack_from('<H',raw,pe+20)[0];start=pe+24+size
 return {raw[start+40*i:start+40*i+8].rstrip(b'\0').decode():struct.unpack_from('<I',raw,start+40*i+36)[0] for i in range(count)}
actual=sections(efi);prior=sections((Path(recipes['private_directory'])/'BdsDxe/OUTPUT/BdsDxe.efi').read_bytes())
assert actual==prior and not any(flags&0x80000000 and flags&0x20000000 for flags in actual.values())
assert sha(OUT/'BdsDxe.dll')==intent['DLL_sha256']
assert all(sha(Path(name))==digest for name,digest in previous['original41_libraries'].items())
result=dict(passed=True,private_output=str(OUT),commands=commands+[row],source_sha256=sha(HERE/'PlatformBm.c.candidate'),
 current_instant_current_parameter_preserved=True,builtin_PD5V_parameter_from_actual_Image505=proof['actual_builtin_parameter'],
 one_object_compiled=True,original40_other_libraries_reused=True,original41_libraries_unchanged=True,
 original_compile_and_link_replayed=False,standard_link_warnings=dict(normalized_equal_original_passed_R2=True,baseline_sha256=sha(baseline),observed_sha256=sha(observed)),
 ARM64_PE32plus_boot_service_driver_verified=True,final_PE_section_flags_equal_original_R2=actual,final_PE_has_no_WX_section=True,
 outputs={name:dict(sha256=sha(OUT/name),bytes=(OUT/name).stat().st_size) for name in ['PlatformBm.obj','PlatformBootManagerLib.lib','BdsDxe.dll','BdsDxe.efi']},
 boot_or_logdump_packed=False,phone_accessed=False,installed=False)
with (HERE/'firmware-build-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,EFI=result['outputs']['BdsDxe.efi'],original_compile_and_link_replayed=False,PE_sections=actual)))
