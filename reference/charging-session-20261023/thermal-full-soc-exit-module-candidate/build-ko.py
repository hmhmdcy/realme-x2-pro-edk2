"""Build one private charger module for Image502; no device or installation."""
from pathlib import Path
import hashlib, importlib.util, json, os, re, shutil, stat, subprocess, sys, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = HERE.parent/'thermal-full-soc-exit-candidate'
R8 = HERE.parent/'r8-source-integration/kernel-sources/drivers/power/supply'
IMAGE = REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
BASE = Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
OUT = Path('/home/cy122/charging-management-20261023/thermal-full-soc-exit-module-01')
EXPORT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/thermal-full-soc-exit-module-private-01')
AUTHOR_DELIVERY = '780e6591e09062da575910f1a771fd5a1605df416f79f8f9740298b844239e25'
def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def save(p, value):
    Path(p).write_text(json.dumps(value, indent=2)+'\n')
def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def source_inputs():
    if sys.flags.optimize: raise RuntimeError('Non-optimized Python required')
    assert sha(AUTHOR/'delivery.json') == AUTHOR_DELIVERY
    delivery = json.loads((AUTHOR/'delivery.json').read_bytes()); assert delivery['passed']
    for name, row in delivery['files'].items(): assert sha(AUTHOR/name) == row['sha256']
    test = json.loads((AUTHOR/'test-result.json').read_bytes()); assert test['passed']
    baseline = json.loads((REF/'charging-management-20261023/thermal-bands-build-result.json').read_bytes())
    assert baseline['passed'] and baseline['module_sha256'] == '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'
    for name, digest in baseline['sources'].items(): assert sha(R8/name) == digest
    paths = {name:R8/name for name in baseline['sources']}
    for name in ['samurai-mp2650.c','mp2650-core.h','oem-full-cycle.h']:
        assert name in delivery['files']; paths[name] = AUTHOR/name
    reattach = HERE.parent/'charger-reattach-observation-candidate'
    assert sha(reattach/'delivery.json') == '6aa4d49a203258ae70f84308eb70119207e9aa1fa2ac5862ca9b88d7cf215138'
    assert sha(reattach/'reattach-observation.h') == '49cb61042d431492d91ccad917f197cbbe2fff58bc53e378aeb92c573e9666c1'
    paths['reattach-observation.h'] = reattach/'reattach-observation.h'
    includes = set(re.findall(r'^#include "([a-z0-9-]+\.h)"', paths['samurai-mp2650.c'].read_text(), re.M))
    assert not includes-set(paths),includes-set(paths)
    return paths

def main():
    paths = source_inputs()
    if sys.argv[1:] in ([], ['--check-local']):
        print(json.dumps({'passed':True,'source_files':list(paths),'hardware_access':False})); return
    assert sys.argv[1:] == ['--execute'] and os.geteuid()==0
    assert not OUT.exists() and not EXPORT.exists() and not (HERE/'ko-result.json').exists(), 'Unique output exists; inspect original process, do not replay'
    old_builder = REF/'charging-oem-audit-20261023/protection-query-observer-module-candidate/build-ko.py'
    assert sha(old_builder)=='6d484f62844c4976c928ab9a6e81fee0851076a33ab188974dd06cbaf689262f'
    util = load_module(old_builder, 'reused_private_module_util')
    assert sha(IMAGE/'build-result.json')=='feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6'
    assert sha(BASE/'build/.config')=='23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    assert sha(BASE/'build/arch/arm64/boot/Image')=='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'
    assert sha(BASE/'build/vmlinux.symvers')=='84f5fc338ea72a6d71b23da50562f89c7963af50675956d3e0aff30540df4d47'
    helper = REF/'kernel284/storage.py'
    assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
    backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
    assert not backing.is_symlink() and stat.S_ISREG(backing.stat().st_mode) and backing.stat().st_size==32*1024**3
    storage = load_module(helper, 'original_charger_module_storage284')
    shared=storage.mounted_build(); assert shared==Path('/mnt/samurai-full282/build')
    tracked = list(paths.values())+[AUTHOR/'delivery.json',AUTHOR/'test-result.json',old_builder,helper,Path(__file__)]
    tracked += [BASE/'build'/name for name in ['.config','Module.symvers','vmlinux.symvers','vmlinux.o','arch/arm64/boot/Image','include/generated/autoconf.h','include/generated/utsrelease.h']]
    tracked += [BASE/'source354'/name for name in ['Makefile','drivers/power/supply/Makefile','include/linux/power_supply.h']]
    tracked += [shared/name for name in ['.config','Module.symvers','arch/arm64/boot/Image','include/generated/autoconf.h']]
    old_module=Path('/home/cy122/charging-management-20261023/thermal-bands-candidate/kbuild/drivers/power/supply/samurai-mp2650.ko')
    assert sha(old_module)=='10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'
    tracked.append(old_module)
    original97c=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko')
    assert sha(original97c)=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
    tracked += [original97c,HERE.parent/'charger-reattach-observation-candidate/reattach-observation.h',
                Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/forward-two-files.tar.gz'),
                Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/manifest-new.json')]
    before={str(p):sha(p) for p in tracked}
    OUT.mkdir(mode=0o700); source=OUT/'source-view'; build=OUT/'kbuild'
    result={'passed':False,'source_delivery_sha256':AUTHOR_DELIVERY,'sources':{n:sha(p) for n,p in paths.items()},
            'old11groups91assertions_reused_not_rerun':True,'current97c_or_manifest_changed':False,
            'device_access':False,'installed':False,'new_Image':False,'SDK_used':False,'commands':[],'before':before}
    try:
        def branch(src,dst,branches):
            for p in src.iterdir():
                if p.name=='.git':continue
                q=dst/p.name
                if p.name in branches:q.mkdir();branch(p,q,branches[p.name])
                else:q.symlink_to(p,target_is_directory=p.is_dir())
        source.mkdir(); branch(BASE/'source354',source,{'drivers':{'power':{'supply':{}}}})
        supply=source/'drivers/power/supply'; makefile=supply/'Makefile'
        assert makefile.is_symlink(); makefile.unlink()
        makefile.write_bytes((BASE/'source354/drivers/power/supply/Makefile').read_bytes()+b'\nobj-m += samurai-mp2650.o\n')
        for name,p in paths.items():
            dest=supply/name; assert not dest.exists() and not dest.is_symlink(); shutil.copy2(p,dest)
        build.mkdir()
        for name in ['.config','Module.symvers','vmlinux.symvers']:shutil.copy2(BASE/'build'/name,build/name)
        (build/'vmlinux.o').symlink_to(BASE/'build/vmlinux.o'); (OUT/'tmp').mkdir()
        env=dict(os.environ)
        for name in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG','SOURCE_DATE_EPOCH','KBUILD_EXTRA_SYMBOLS','KCFLAGS','CFLAGS_KERNEL','CFLAGS_MODULE','LDFLAGS','MAKEFLAGS','MFLAGS','LOCALVERSION']:env.pop(name,None)
        env.update(PATH='/home/cy122/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin:/home/cy122/.cargo/bin:'+env['PATH'],
                   RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_VERSION='502',
                   KBUILD_BUILD_TIMESTAMP='Tue Oct 20 03:03:47 UTC 2026',TMPDIR=str(OUT/'tmp'))
        argv=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','KCFLAGS=-Werror','-j4']
        for target,label in [('modules_prepare','prepare'),('drivers/power/supply/samurai-mp2650.ko','module')]:
            started=time.monotonic(); log=OUT/(label+'.log')
            with log.open('xb') as stream:
                child=subprocess.Popen(argv+[target],env=env,stdout=stream,stderr=subprocess.STDOUT)
                try:
                    save(OUT/'process.json',{'pid':child.pid,'terminal':False,'target':target})
                    print(json.dumps({'phase':label,'pid':child.pid,'started':True}),flush=True)
                finally:rc=child.wait()
            row={'pid':child.pid,'terminal':True,'returncode':rc,'target':target,'seconds':round(time.monotonic()-started,3),'log_sha256':sha(log)}
            save(OUT/'process.json',row);result['commands'].append(row); print(json.dumps(row),flush=True);assert rc==0
        diagnostics=[line for name in ['prepare.log','module.log'] for line in (OUT/name).read_text(errors='replace').splitlines() if re.search(r'\b(?:warning|error):|undefined!',line,re.I)]
        assert not diagnostics,diagnostics
        ko=build/'drivers/power/supply/samurai-mp2650.ko'
        run=util.run_output
        assert run(['modinfo','-F','name',str(ko)]).strip()=='samurai_mp2650'
        assert run(['modinfo','-F','intree',str(ko)]).strip()=='Y' and not run(['modinfo','-F','depends',str(ko)]).strip()
        vermagic=run(['modinfo','-F','vermagic',str(ko)]).strip()
        assert vermagic=='7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64'
        assert sha(build/'.config')==sha(BASE/'build/.config')
        assert sha(build/'include/generated/autoconf.h')==sha(BASE/'build/include/generated/autoconf.h')
        exports={r[1]:r for r in (line.split() for line in (BASE/'build/vmlinux.symvers').read_text().splitlines())}
        assert len(exports)==15097 and all(r[2]=='vmlinux' for r in exports.values())
        undefined=[line.split() for line in run(['aarch64-linux-gnu-nm','-u',str(ko)]).splitlines()]
        assert all(len(r)==2 and r[0]=='U' and r[1] in exports for r in undefined)
        imports={r[1]:exports[r[1]] for r in undefined};save(OUT/'Image502-import-map.json',imports)
        module_note,build_id=util.note(ko.read_bytes());(OUT/'note.gnu.build-id').write_bytes(module_note)
        EXPORT.mkdir(mode=0o700);private=EXPORT/'samurai-mp2650-thermal-full-soc-exit-private.ko';shutil.copy2(ko,private)
        shutil.copy2(OUT/'note.gnu.build-id',EXPORT/'note.gnu.build-id'); assert sha(private)==sha(ko)
        assert all(sha(supply/name)==sha(p) for name,p in paths.items())
        result.update(passed=True,module_path=str(ko),private_module_path=str(private),module_sha256=sha(ko),module_bytes=ko.stat().st_size,
                      module_note_sha256=hashlib.sha256(module_note).hexdigest(),GNU_build_id=build_id,vermagic=vermagic,intree=True,
                      config_and_autoconf_exact_Image502=True,strong_import_count=len(imports),all_imports_from_Image502_builtin=True,
                      import_map_sha256=sha(OUT/'Image502-import-map.json'),diagnostics=[],runtime_loaded_or_type_ABI_proved=False)
    except BaseException as error:result['error']=repr(error);raise
    finally:
        after={str(p):sha(p) for p in tracked};result.update(after=after,tracked_inputs_unchanged=before==after)
        result['passed']=result['passed'] and before==after;save(OUT/'ko-result.json',result);save(HERE/'ko-result.json',result)
        print(json.dumps({k:result.get(k) for k in ['passed','module_sha256','module_bytes','module_note_sha256','strong_import_count','tracked_inputs_unchanged','error']}),flush=True)
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
