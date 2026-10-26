from pathlib import Path
import hashlib, json, os, re, resource, shutil, struct, subprocess, tarfile, sys

k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel166')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel166')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((ref/'source-validation.json').read_text())
for name,digest in source['source_sha256'].items():
    assert sha(k/name)==digest
assert json.loads((ref/'host-tests-validation.json').read_text())['transactions']['passed']==14
baseline=json.loads((ref.parent/'kernel163/build-package-validation.json').read_text())
for name,digest in {**baseline['source_sha256'],**baseline['prior_display_source_hashes_verified']}.items():
    assert sha(k/name)==digest
patch='''Subject: [PATCH] slimbus: qcom-ngd: preserve PM and DMA lifecycle on failures

Propagate runtime-resume and DMA setup failures to callers, abort transfers
after failed PM get, and retain DMA when the remote rejects suspension.
Release coherent queues after termination and keep QMI readiness until
disconnect. Reset stale runtime-PM state at service-up after SSR.

ASoC: wcd934x: stop hardware initialization after transport or efuse errors
and defer probing when the SLIM device is down. Allocate Class-H state only
after the version has been read successfully.

'''+subprocess.check_output(['git','diff','--',*source['modified_files']],cwd=k,text=True)
(ref/'audio-lifecycle.patch').write_text(patch)
check=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'audio-lifecycle.patch')],cwd=k,capture_output=True,text=True)
(out/'checkpatch.txt').write_text(check.stdout+check.stderr)
assert check.returncode==0,check.stdout
assert subprocess.run(['git','diff','--check'],cwd=k).returncode==0
env=os.environ.copy();env.update(PATH='/home/cy122/.cargo/bin:'+env['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='166')
base=['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory']
def limit():
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
def make(label,args):
    log=out/(label+'-build-private.log')
    if '--resume-after-inherited-warning' in sys.argv and label in ['changed-w1','full']:
        assert log.exists()
        if label=='full': assert '  OBJCOPY arch/arm64/boot/Image' in log.read_text()
    else:
        assert not log.exists(),log
        with log.open('wb') as stream:
            subprocess.run(base+args,cwd=k,env=env,stdout=stream,stderr=subprocess.STDOUT,preexec_fn=limit,check=True)
    diagnostics=re.findall(r'^.*\b(?:warning|error):.*$',log.read_text(),re.M)
    expected="drivers/tty/serial/eud_earlycon.c:75:13: warning: ‘eud_wait_tx’ defined but not used [-Wunused-function]"
    assert not diagnostics or label=='full' and diagnostics==[expected],(log,diagnostics)
    if diagnostics:
        assert (k/'drivers/tty/serial/eud_earlycon.c').read_bytes()==subprocess.check_output(['git','show','HEAD:drivers/tty/serial/eud_earlycon.c'],cwd=k)
    print('K166_'+label.upper()+'_PASS',flush=True)
make('changed-w1',['W=1','-j4','drivers/slimbus/qcom-ngd-ctrl.o','drivers/slimbus/messaging.o','sound/soc/codecs/wcd934x.o'])
make('full',['-j4','Image','modules','qcom/sm8150-samurai.dtb'])
assert (k/'.config').read_bytes()==(out/'config-before-private').read_bytes()
image=out/'Image-k166-audio-private';assert not image.exists();shutil.copyfile(k/'arch/arm64/boot/Image',image)
assert '#166 SMP PREEMPT' in subprocess.check_output(['strings',str(image)],text=True)
modules=k.parent/'modules-root166';assert not modules.exists();modules.mkdir(mode=0o700)
make('install',['INSTALL_MOD_PATH='+str(modules),'INSTALL_MOD_STRIP=1','modules_install'])
release=(k/'include/config/kernel.release').read_text().strip()
(modules/'lib/modules'/release/'build').unlink()
depmod=subprocess.run(['depmod','-e','-F',str(k/'System.map'),'-b',str(modules),release],capture_output=True)
assert depmod.returncode==0 and not depmod.stdout and not depmod.stderr
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as archive:
    old={m.name:archive.extractfile(m).read() for m in archive if m.isfile() and m.name.endswith('.ko')}
new={str(p.relative_to(modules)):p.read_bytes() for p in modules.rglob('*.ko')}
assert new.keys()==old.keys() and len(new)==770
def note(data):
    offset=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58)
    headers=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
    strings=data[headers[index][4]:headers[index][4]+headers[index][5]]
    for row in headers:
        if strings[row[0]:].split(b'\x00',1)[0]==b'.note.gnu.build-id': return row[4],row[5]
    raise AssertionError('Missing build ID')
changed=[]
for name,before in old.items():
    after=new[name]
    if after==before: continue
    assert note(after)==note(before),name
    offset,size=note(before)
    assert after[:offset]+before[offset:offset+size]+after[offset+size:]==before,name
    changed.append(name)
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
assert sha(dtb)==baseline['dtb_sha256']
rollback=out.parent/'kernel163/logdump-k163-early-reset.img'
assert sha(rollback)==baseline['logdump_sha256']
target=out/'logdump-k166-audio.img';assert not target.exists();shutil.copyfile(rollback,target)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==dtb.read_bytes()
fat=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True);assert fat.returncode==0
(out/'fat-check.txt').write_bytes(fat.stdout+fat.stderr)
assert set(subprocess.check_output(['git','diff','--name-only'],cwd=k,text=True).splitlines())==set(source['modified_files'])
report=dict(stage=166,kernel_build=166,software_generation=132,release=release,
            image_sha256=sha(image),image_bytes=image.stat().st_size,logdump_sha256=sha(target),
            logdump_bytes=target.stat().st_size,rollback163_sha256=sha(rollback),
            dtb_sha256=sha(dtb),source_sha256=source['source_sha256'],
            config_unchanged=True,dtb_unchanged=True,prior_display_sources_unchanged=True,
            modules_count=770,module_build_id_only_differences=changed,modules132_runtime_compatible=True,
            fat_readback_exact=True,fat_check_pass=True,checkpatch_pass=True,audio_object_warnings=0,
            build_warnings=1,inherited_unchanged_eud_unused_function_warning=True,
            flash_partitions=['logdump'],boot164_retained=True,deployed=False)
for folder in [ref,out]:
    (folder/'build-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
