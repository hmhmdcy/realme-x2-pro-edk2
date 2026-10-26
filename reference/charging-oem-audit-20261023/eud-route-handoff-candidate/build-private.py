"""One BDS object, EFI parser and new reader; no make, packing or install."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shlex,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_bytes());assert t['passed'] and all(sha(HERE/n)==h for n,h in t['files'].items())
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_EFI_handoff_build',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);BUILD=m.mounted_build();SOURCE=(BUILD/'source').resolve()
assert SOURCE==Path('/mnt/samurai-full282/source354')
OUT=Path('/home/cy122/charging-management-20261023/eud-route-handoff-objects-01');assert not OUT.exists()
old=json.loads((REF/'charging-session-20261023/eud-bds-r2-build/result.json').read_bytes());assert old['passed']
bds_recipe=old['child']['commands'][0]['argv'];original_bds=Path(bds_recipe[-1]);response=Path(next(word[1:] for word in bds_recipe if word.startswith('@')))
assert '-DSAMURAI_LINUX_KERNEL' in response.read_text() and '-DSAMURAI_ENABLE_EUD' in response.read_text()
efi_cmd=BUILD/'drivers/firmware/efi/.efi.o.cmd';saved=efi_cmd.read_text().splitlines()[0]
assert saved.startswith('savedcmd_drivers/firmware/efi/efi.o := ')
kernel_recipe=shlex.split(saved.split(' := ',1)[1]);assert kernel_recipe[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in kernel_recipe
paths=[helper,BUILD/'.config',BUILD/'include/generated/autoconf.h',BUILD/'Module.symvers',efi_cmd,BUILD/'drivers/firmware/efi/efi.o',
    SOURCE/'drivers/firmware/efi/efi.c',SOURCE/'include/linux/efi.h',original_bds,original_bds.parent/'PlatformBm.h',response]
before={str(p):sha(p) for p in paths}
assert sha(SOURCE/'drivers/firmware/efi/efi.c')==json.loads((HERE/'source-result.json').read_bytes())['source_records']['efi.c']['sha256']
OUT.mkdir();(OUT/'tmp').mkdir();include=OUT/'include/linux/firmware';include.mkdir(parents=True)
for name in ['samurai-eud-handoff.h','samurai-eud-handoff-wire.h']:(include/name).write_bytes((HERE/name).read_bytes())
bds_source=OUT/'PlatformBm.c';bds_source.write_bytes((HERE/'PlatformBm.c.candidate').read_bytes())
(OUT/'samurai-eud-handoff-wire.h').write_bytes((HERE/'samurai-eud-handoff-wire.h').read_bytes())
commands=[];phases=[]
def run(name,argv,cwd):
    commands.append(argv)
    child=subprocess.Popen(argv,cwd=cwd,env={**os.environ,'TMPDIR':str(OUT/'tmp')},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();child.wait();(OUT/(name+'.stdout')).write_bytes(stdout);(OUT/(name+'.stderr')).write_bytes(stderr)
    row=dict(name=name,pid=child.pid,original_child_terminal=True,returncode=child.returncode,diagnostic_bytes=len(stderr));phases.append(row)
    assert child.returncode==0 and not stderr,(row,stderr.decode()[-3500:])
argv=list(bds_recipe);argv[-1]=str(bds_source);argv[argv.index('-o')+1]=str(OUT/'PlatformBm.o');argv[argv.index('-MF')+1]=str(OUT/'PlatformBm.d')
argv[1:1]=['-Werror','-I'+str(original_bds.parent)];run('BDS',argv,Path(old['child']['commands'][0]['cwd']))
for name,source in [('efi',HERE/'efi.c'),('samurai-eud-handoff',HERE/'samurai-eud-handoff.c')]:
    argv=list(kernel_recipe);assert argv[-1]==str(SOURCE/'drivers/firmware/efi/efi.c')
    argv[-1]=str(source);argv[argv.index('-o')+1]=str(OUT/(name+'.o'))
    argv=[('-Wp,-MMD,'+str(OUT/(name+'.d'))) if word.startswith('-Wp,-MMD,') else word for word in argv]
    argv[1:1]=['-Werror','-DCONFIG_QCOM_SAMURAI_EUD_HANDOFF=1','-I'+str(OUT/'include'),'-I'+str(SOURCE/'drivers/firmware/efi')]
    run(name,argv,BUILD)
partial=OUT/'kernel-interface-only.o';command=['aarch64-linux-gnu-ld','-r','--fatal-warnings','-o',str(partial),str(OUT/'efi.o'),str(OUT/'samurai-eud-handoff.o')]
run('kernel-interface',command,OUT)
undefined=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(partial)],text=True).splitlines()
assert not any('samurai_eud_handoff_' in line for line in undefined)
old_bds=Path(old['private_directory'])/'PlatformBootManagerLib/OUTPUT/PlatformBm.obj'
assert sha(old_bds)=='7f86d1ccab2100fcf836e15b768f22cba40460a98984d1f5a4884c2bc99d7b0e'
def imports(path):return {line.split()[-1] for line in subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(path)],text=True).splitlines()}
added=imports(OUT/'PlatformBm.o')-imports(old_bds)
link_recipe=next(row['argv'] for row in old['child']['commands'] if row['stage']=='link')
list_path=Path(next(re.search(r'@([^,]+)',word).group(1) for word in link_recipe if word.startswith('-Wl,--start-group,@')))
libraries=[Path(word) for word in shlex.split(list_path.read_text())];assert len(libraries)==41 and all(path.is_file() for path in libraries)
library_before={str(p):sha(p) for p in libraries}
definitions=subprocess.check_output(['aarch64-linux-gnu-nm','-A','-g','--defined-only',*[str(p) for p in libraries]],text=True,stderr=subprocess.DEVNULL).splitlines()
providers={symbol:[line for line in definitions if line.split() and line.split()[-1]==symbol] for symbol in sorted(added)}
assert all(providers.values()),providers
after={str(p):sha(p) for p in paths};assert before==after and library_before=={str(p):sha(p) for p in libraries}
result=dict(passed=True,private_output=str(OUT),phases=phases,commands=commands,
    objects={p.name:sha(p) for p in OUT.glob('*.o')},new_BDS_imports_resolved_from_original41=providers,
    original41_libraries=library_before,original_shared_before=before,original_shared_after=after,shared_unchanged=True,
    future_kernel_option_command_only=True,shared_config_changed=False,Image_or_firmware_linked=False,partial_kernel_interface_only=True,
    files={name:sha(HERE/name) for name in ['PlatformBm.c.candidate','efi.c','samurai-eud-handoff.c','samurai-eud-handoff.h','samurai-eud-handoff-wire.h','firmware-record-functions.inc']},
    phone_accessed=False,SDK_or_make_invoked=False,route_ownership_created=False)
with (HERE/'build-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,phases=phases,new_BDS_imports=list(providers),shared_unchanged=True,route_ownership_created=False)))
