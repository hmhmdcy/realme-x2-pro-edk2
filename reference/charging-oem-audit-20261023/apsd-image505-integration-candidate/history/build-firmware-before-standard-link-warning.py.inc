"""Recompile one BDS object, reuse the original libraries and link its EFI."""
from pathlib import Path
import hashlib,json,os,re,shlex,struct,subprocess,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];HANDOFF=HERE.parent/'eud-route-handoff-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((HERE/'dtb-and-command-r2-result.json').read_bytes());assert proof['passed']
assert sha(HERE/'PlatformBm.c.candidate')==proof['BDS_source_sha256']
previous=json.loads((HANDOFF/'build-result.json').read_bytes());recipes=json.loads((REF/'charging-session-20261023/eud-bds-r2-build/result.json').read_bytes())
assert previous['passed'] and recipes['passed']
OUT=Path('/home/cy122/charging-management-20261023/apsd-image505-bds-01');assert not OUT.exists();OUT.mkdir();(OUT/'tmp').mkdir()
source=OUT/'PlatformBm.c';source.write_bytes((HERE/'PlatformBm.c.candidate').read_bytes())
(OUT/'samurai-eud-handoff-wire.h').write_bytes((HANDOFF/'samurai-eud-handoff-wire.h').read_bytes())
old_libraries={Path(name):digest for name,digest in previous['original41_libraries'].items()}
assert len(old_libraries)==41 and all(sha(path)==digest for path,digest in old_libraries.items())
commands=[]
def run(name,argv,cwd):
 started=time.monotonic();child=subprocess.Popen(argv,cwd=cwd,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 stdout,stderr=child.communicate();child.wait();(OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
 row=dict(name=name,pid=child.pid,terminal=True,returncode=child.returncode,argv=argv,cwd=str(cwd),seconds=time.monotonic()-started,diagnostic_bytes=len(stderr));commands.append(row)
 (OUT/'commands-private.json').write_text(json.dumps(commands,indent=2)+'\n')
 assert child.returncode==0 and not stderr,(name,child.returncode,stderr.decode())
compile_command=list(previous['commands'][0]);compile_command[-1]=str(source);compile_command[compile_command.index('-o')+1]=str(OUT/'PlatformBm.obj');compile_command[compile_command.index('-MF')+1]=str(OUT/'PlatformBm.d')
run('compile-BDS',compile_command,Path(recipes['child']['commands'][0]['cwd']))
old_obj=Path(previous['private_output'])/'PlatformBm.o';assert sha(old_obj)==previous['objects']['PlatformBm.o']
def imports(path):return {line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(path)],text=True).splitlines()}
assert imports(OUT/'PlatformBm.obj')==imports(old_obj)
library=OUT/'PlatformBootManagerLib.lib';run('archive-one-object',['aarch64-linux-gnu-gcc-ar','cr',str(library),str(OUT/'PlatformBm.obj')],OUT)
assert subprocess.check_output(['aarch64-linux-gnu-ar','t',str(library)],text=True).splitlines()==['PlatformBm.obj']
link_row=next(row for row in recipes['child']['commands'] if row['stage']=='link');link=list(link_row['argv'])
argument=next(word for word in link if word.startswith('-Wl,--start-group,@'));list_path=Path(re.search(r'@([^,]+)',argument).group(1));libraries=shlex.split(list_path.read_text())
replaced=[name for name in libraries if Path(name).name=='PlatformBootManagerLib.lib'];assert len(replaced)==1
new_libraries=[str(library) if name==replaced[0] else name for name in libraries];file_list=OUT/'static-library-files.lst';file_list.write_text('\n'.join(shlex.quote(name) for name in new_libraries)+'\n')
link[link.index('-o')+1]=str(OUT/'BdsDxe.dll')
link=[word.replace('@'+str(list_path),'@'+str(file_list)) for word in link]
link=[('-Wl,-e,_ModuleEntryPoint,-Map,'+str(OUT/'BdsDxe.map')) if word.startswith('-Wl,-e,_ModuleEntryPoint,-Map,') else word for word in link]
run('link-BDS-DXE',link,Path(link_row['cwd']))
gen=list(next(row['argv'] for row in recipes['child']['commands'] if row['stage']=='GenFw'));gen[gen.index('-o')+1]=str(OUT/'BdsDxe.efi');gen[-1]=str(OUT/'BdsDxe.dll');run('GenFw',gen,OUT)
efi=(OUT/'BdsDxe.efi').read_bytes();assert efi[:2]==b'MZ';offset=struct.unpack_from('<I',efi,0x3c)[0]
assert efi[offset:offset+4]==b'PE\0\0' and struct.unpack_from('<H',efi,offset+4)[0]==0xaa64 and struct.unpack_from('<H',efi,offset+24)[0]==0x20b
assert struct.unpack_from('<H',efi,offset+24+68)[0]==11
assert proof['candidate_cmdline'].encode('utf-16-le') in efi
assert all(sha(path)==digest for path,digest in old_libraries.items())
result=dict(passed=True,private_output=str(OUT),commands=commands,source_sha256=sha(HERE/'PlatformBm.c.candidate'),
 current_instant_current_parameter_preserved=True,builtin_PD5V_parameter_from_actual_Image505=proof['actual_builtin_parameter'],
 one_object_compiled=True,original40_other_libraries_reused=True,original41_libraries_unchanged=True,new_BDS_imports_exact_checked_handoff=True,
 outputs={name:dict(sha256=sha(OUT/name),bytes=(OUT/name).stat().st_size) for name in ['PlatformBm.obj','PlatformBootManagerLib.lib','BdsDxe.dll','BdsDxe.efi']},
 ARM64_PE32plus_boot_service_driver_verified=True,boot_or_logdump_packed=False,phone_accessed=False,installed=False)
with (HERE/'firmware-build-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,EFI=result['outputs']['BdsDxe.efi'],compiled_objects=1,other_libraries_reused=40)))
