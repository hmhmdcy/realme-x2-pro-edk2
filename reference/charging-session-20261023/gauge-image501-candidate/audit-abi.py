"""Read the terminal private B501 outputs and cached modules; never build/mount."""
from pathlib import Path
import hashlib, importlib.util, json, os, re, subprocess, sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OUT=Path('/home/cy122/charging-management-20261023/gauge-image501-B-01')
BASE=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')
PRIVATE=Path('/mnt/e/edk2-samurai-out')
spec=importlib.util.spec_from_file_location('frozen_baseline',HERE.parent/'gauge-image363-baseline/run-baseline.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
sha=base.sha;save=base.save
result=json.loads((HERE/'build-result.json').read_bytes())
assert result['passed'] and json.loads((OUT/'namespace-process.json').read_bytes())['terminal']
BUILD=OUT/'build'
def output(argv):return subprocess.check_output(argv,text=True)
def symbols(path):
    rows={}
    for line in path.read_text().splitlines():
        f=line.split()
        if len(f)>=4:
            assert f[1] not in rows
            rows[f[1]]=f
    return rows
old=symbols(BASE/'build/Module.symvers')
fresh=symbols(BUILD/'vmlinux.symvers')
old_builtin={n:r for n,r in old.items() if r[2]=='vmlinux'}
assert fresh==old_builtin
assert sha(BUILD/'Module.symvers')==sha(BASE/'build/Module.symvers')=='0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223'
def elf_exports(path):
    rows=output(['aarch64-linux-gnu-nm','-a','--defined-only',str(path)]).splitlines()
    return {r.split()[-1].removeprefix('__ksymtab_') for r in rows if r.split()[-1].startswith('__ksymtab_') and r.split()[-1]!='__ksymtab_strings'}
old_binary=elf_exports(BASE/'build/vmlinux')
new_binary=elf_exports(BUILD/'vmlinux')
assert old_binary==new_binary==set(fresh),'Actual ELF export names differ from symvers'
def archive_members(path):
    answer=[]
    for n in output(['aarch64-linux-gnu-ar','t',str(path)]).splitlines():
        p=Path(n)
        if not p.is_absolute():p=path.parent/p
        canonical=Path('/mnt/samurai-full282/build')
        answer.append(str(p.relative_to(canonical if p.is_relative_to(canonical) else BUILD)))
    return answer
link=json.loads((base.PLAN/'link-inputs.json').read_bytes())
final=json.loads((base.PLAN/'final-link-inputs.json').read_bytes())
assert archive_members(BUILD/'vmlinux.a')==list(link['members'])
assert archive_members(BUILD/'drivers/firmware/efi/libstub/lib.a')==list(final['libstub_members'])
config=(BUILD/'.config').read_text()
assert '# CONFIG_MODVERSIONS is not set' in config
assert '# CONFIG_MODULE_SIG is not set' in config
assert sha(BUILD/'.config')==base.EXPECTED['config']
release='7.3.0-rc6-rmx1931-samurai-k363+'
assert (BUILD/'include/config/kernel.release').read_text().strip()==release
source_before=json.loads((OUT/'source354-baseline-before.json').read_bytes())
source_after=base.inventory(OUT/'source354')
source_delta=[n for n in source_before.keys()|source_after.keys() if source_before.get(n)!=source_after.get(n)]
assert source_delta==['drivers/power/supply/bq27xxx_battery.c']
old_objects={n:r['sha256'] for n,r in json.loads((OUT/'build-baseline-before.json').read_bytes()).items() if n.endswith('.o') and r['kind']=='file'}
new_objects={str(p.relative_to(BUILD)):sha(p) for p in BUILD.rglob('*.o') if p.is_file() and not p.is_symlink()}
object_delta=[{'path':n,'before':old_objects.get(n),'after':new_objects.get(n)} for n in sorted(old_objects.keys()|new_objects.keys()) if old_objects.get(n)!=new_objects.get(n)]
save(OUT/'all-object-delta.json',object_delta)
frozen_source=(OUT/'source354/drivers/power/supply/bq27xxx_battery.c').read_text()
assert 'static bool samurai_instant_current;' in frozen_source
assert 'module_param(samurai_instant_current, bool, 0444);' in frozen_source
param=[l.split() for l in output(['aarch64-linux-gnu-nm','-a',str(BUILD/'drivers/power/supply/bq27xxx_battery.o')]).splitlines() if l.split()[-1]=='samurai_instant_current']
assert len(param)==1 and param[0][-2]=='b','Opt-in variable not zero-initialized BSS'
module_inventory=PRIVATE/'kernel363/installed-module-inventory-private.json'
inventory=json.loads(module_inventory.read_bytes());assert len(inventory)==778
module_root=Path('/mnt/samurai-full282/modules363/lib/modules')/release
module_rows={}; all_old_names=set(old)
def imports(path):
    strong=set();weak=set()
    for line in output(['aarch64-linux-gnu-nm','-u',str(path)]).splitlines():
        f=line.split()
        if not f:continue
        (strong if f[-2]=='U' else weak).add(f[-1])
    return strong,weak
for n,d in inventory.items():
    p=module_root/n;assert sha(p)==d,n
    strong,weak=imports(p)
    before_missing=strong-all_old_names
    after_missing=strong-(set(fresh)|{s for s,r in old.items() if r[2]!='vmlinux'})
    assert before_missing==after_missing
    assert not after_missing,(n,sorted(after_missing))
    module_rows[n]={'sha256':d,'strong_import_count':len(strong),'weak_import_count':len(weak),
                    'imports_from_unchanged_builtins':sorted(strong&set(fresh)),
                    'unresolved_imports':sorted(after_missing)}
save(OUT/'original-module-imports.json',module_rows)
# Reuse the exact formal481/cache mapping; these are cached files, not a new runtime attestation.
abi=json.loads((base.PLAN/'abi-payload.json').read_bytes())
wrapper=PRIVATE/'kernel481/formal-expected-private.json'
assert sha(wrapper)==abi['formal_camera_wrapper_sha256']=='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
formal=json.loads(wrapper.read_bytes())['expected']
current={}
for name,r in formal['modules'].items():
    matches=list((PRIVATE/'kernel441').glob(Path(r['path']).stem+'-intree-r4.ko'))
    assert len(matches)==1 and sha(matches[0])==r['sha256']
    current[name]=matches[0]
sensor=PRIVATE/'kernel468/s5k3m5-mode2-build2.ko'
assert sha(sensor)==abi['modules']['s5k3m5']['sha256']
current['s5k3m5']=sensor
deps=json.loads((REF/'kernel441/intree-build-validation.json').read_bytes())['modules']
for r in deps:
    if not r['runtime_candidate']:
        p=Path(r['private_path']);assert sha(p)==r['sha256'];current['dependency:'+r['name']]=p
group_exports=set().union(*(elf_exports(p) for p in current.values()))
current_rows={}
for name,p in current.items():
    strong,weak=imports(p)
    unresolved=strong-(set(fresh)|all_old_names|group_exports)
    assert not unresolved,(name,sorted(unresolved))
    vermagic=output(['modinfo','-F','vermagic',str(p)]).strip()
    assert vermagic.split()[0]==release
    current_rows[name]={'sha256':sha(p),'vermagic':vermagic,'strong_import_count':len(strong),
                        'unchanged_builtin_import_count':len(strong&set(fresh)),
                        'unresolved_imports':sorted(unresolved)}
save(OUT/'camera481-cached-module-imports.json',current_rows)
diagnostics=[]
for p in OUT.glob('B-*.log'):
    diagnostics.extend({'log':p.name,'line':s} for s in p.read_text(errors='replace').splitlines() if re.search(r'\b(?:warning|error):',s,re.I))
abi_result={'passed':True,'original_cached_modules':len(module_rows),'camera_and_cached_dependencies':len(current_rows),
 'original_module_inventory_sha256':sha(module_inventory),'formal481_wrapper_sha256':sha(wrapper),
 'builtin_export_count':len(fresh),'actual_ELF_export_names_exact':True,
 'builtin_export_rows_including_class_namespace_CRC_exact':True,'Module_symvers_original_unchanged':True,
 'UTS_RELEASE_unchanged':release,'CONFIG_exact_original':True,'MODVERSIONS':False,'MODULE_SIG':False,
 'public_headers_unchanged':True,'source_changes':source_delta,
 'vmlinux_archive_member_order_exact':True,'libstub_member_order_exact':True,
 'B_param_zero_initialized_BSS':True,'B_param_permission_octal':'0444',
 'all_object_delta':object_delta,'compiler_diagnostics':diagnostics,
 'compatibility_scope':'Unchanged CONFIG/release/headers and non-gauge builtins; exact export names/classes/namespaces and cached module import/provider names. Zero CRC with MODVERSIONS off is not separate type ABI proof. No new runtime/module-load attestation.',
 'old_function_or_object_test_suites_rerun':False,'device_access':False,
 'private_receipts':{n:sha(OUT/n) for n in ['all-object-delta.json','original-module-imports.json','camera481-cached-module-imports.json',
 'namespace-proof.json','source-delta.json','commands.json','phases.json','identity.json','result.json','build-result.json']},
 'logs':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.glob('*.log')}}
save(OUT/'abi-result.json',abi_result);save(HERE/'abi-result.json',abi_result)
print(json.dumps({'passed':True,'builtin_export_count':len(fresh),'cached_original_modules':len(module_rows),
 'current_camera_and_dependencies':len(current_rows),'all_object_delta':object_delta,'compiler_diagnostic_count':len(diagnostics)},indent=2),flush=True)
