from pathlib import Path
import difflib, hashlib, json, os, re, resource, shutil, struct, subprocess, tarfile, sys

os.umask(0o077)
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = json.loads((ref / 'source-validation.json').read_text())
resume = '--resume-after-dtb-property-name' in sys.argv
for n, digest in source['source_sha256'].items():
    assert sha(k / n) == digest, n
assert json.loads((ref / 'host-tests-validation.json').read_text())['all_passed']
baseline = json.loads((ref.parent / 'kernel163/build-package-validation.json').read_text())
for n, digest in {**baseline['source_sha256'], **baseline['prior_display_source_hashes_verified']}.items():
    assert sha(k / n) == digest, n
patch = '''Subject: [PATCH] ASoC: samurai: bind WCD934x headset detection once

Keep RX and TX channel maps while sharing one MBHC jack binding. Route
headset AMIC2 through MIC BIAS2 and gate handset input and speakers from
jack reports. Parse micbias before copying its voltage into MBHC, reject
zero ADC threshold divisors, and retain detection state on failed start.
Propagate micbias and MBHC initialization failures, and use millivolts
for default button thresholds as for device-tree thresholds.

---
'''
for n in source['modified_this_stage']:
    patch += ''.join(difflib.unified_diff((out / 'before-private' / n).read_text().splitlines(True),
                                        (k / n).read_text().splitlines(True), fromfile='a/' + n, tofile='b/' + n))
(ref / 'headset-detection.patch').write_text(patch)
check = subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref / 'headset-detection.patch')], cwd=k, capture_output=True)
(out / 'checkpatch-private.log').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0, check.stdout.decode()
subprocess.run(['git','diff','--check'], cwd=k, check=True)
env = os.environ.copy()
env.update(PATH='/home/cy122/.cargo/bin:' + env['PATH'], RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='172')
base = ['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory']
def limit():
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
def make(label, args):
    log = out / (label + '-build-private.log')
    if resume and label in ['changed-w1','full']:
        assert log.exists()
        if label == 'full': assert '  OBJCOPY arch/arm64/boot/Image' in log.read_text()
    else:
        assert not log.exists(), log
        with log.open('wb') as stream:
            subprocess.run(base + args, cwd=k, env=env, stdout=stream, stderr=subprocess.STDOUT, preexec_fn=limit, check=True)
    diagnostics = re.findall(r'^.*\b(?:warning|error):.*$', log.read_text(), re.M)
    inherited = "drivers/tty/serial/eud_earlycon.c:75:13: warning: ‘eud_wait_tx’ defined but not used [-Wunused-function]"
    assert not diagnostics or label == 'full' and diagnostics == [inherited], (label, diagnostics)
    print('K172_' + label.upper() + '_PASS', flush=True)
make('changed-w1', ['W=1','-j4','sound/soc/qcom/samurai-audio.o','sound/soc/codecs/wcd934x.o','sound/soc/codecs/wcd-mbhc-v2.o'])
make('full', ['-j4','Image','modules','qcom/sm8150-samurai.dtb'])
assert (k / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
image = out / 'Image-k172-headset-private'
if resume: assert image.read_bytes() == (k / 'arch/arm64/boot/Image').read_bytes()
else:
    assert not image.exists(); shutil.copyfile(k / 'arch/arm64/boot/Image', image)
assert '#172 SMP PREEMPT' in subprocess.check_output(['strings',str(image)], text=True)
dtb = out / 'samurai-headset-k172-private.dtb'
if resume: assert dtb.read_bytes() == (k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()
else:
    assert not dtb.exists(); shutil.copyfile(k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', dtb)
namespace = {}
exec(compile((ref.parent / 'kernel104/verify-firmware.py').read_text().split('dt_audit=')[0], 'existing-fdt-parser', 'exec'), namespace)
fdt_nodes = namespace['fdt_nodes']
old = fdt_nodes((out / 'dtb-before171-private').read_bytes()); new = fdt_nodes(dtb.read_bytes())
assert old.keys() == new.keys()
changes = [(p,n) for p in old for n in set(old[p]) | set(new[p]) if old[p].get(n) != new[p].get(n)]
assert sorted(n for p,n in changes) == ['audio-routing','widgets'], changes
for p, n in changes:
    if n == 'widgets':
        assert new[p][n] == old[p][n] + b'Microphone\x00Mic Jack\x00'
    else:
        assert new[p][n].replace(b'AMIC2\x00Mic Jack\x00AMIC2\x00MIC BIAS2\x00AMIC2\x00MCLK\x00', b'') == old[p][n]
modules = k.parent / 'modules-root172'; assert not modules.exists(); modules.mkdir(mode=0o700)
make('install', ['INSTALL_MOD_PATH=' + str(modules), 'INSTALL_MOD_STRIP=1','modules_install'])
release = (k / 'include/config/kernel.release').read_text().strip()
(modules / 'lib/modules' / release / 'build').unlink()
p = subprocess.run(['depmod','-e','-F',str(k / 'System.map'),'-b',str(modules),release], capture_output=True)
assert p.returncode == 0 and not p.stdout and not p.stderr
with tarfile.open(out.parent / 'kernel132/modules-k132-private.tar.gz') as archive:
    previous = {m.name:archive.extractfile(m).read() for m in archive if m.isfile() and m.name.endswith('.ko')}
current = {str(p.relative_to(modules)):p.read_bytes() for p in modules.rglob('*.ko')}
assert current.keys() == previous.keys() and len(current) == 770
def note(data):
    offset = struct.unpack_from('<Q',data,40)[0]; size,count,index = struct.unpack_from('<HHH',data,58)
    headers = [struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
    strings = data[headers[index][4]:headers[index][4]+headers[index][5]]
    for row in headers:
        if strings[row[0]:].split(b'\0',1)[0] == b'.note.gnu.build-id': return row[4],row[5]
    raise AssertionError('Missing build ID')
changed = []
for n, before in previous.items():
    after = current[n]
    if before == after: continue
    assert note(after) == note(before), n
    offset, size = note(before)
    assert after[:offset] + before[offset:offset+size] + after[offset+size:] == before, n
    changed.append(n)
assert set(subprocess.check_output(['git','diff','--name-only'], cwd=k, text=True).splitlines()) == set(source['tracked_modified_files'])
for n, digest in source['source_sha256'].items(): assert sha(k / n) == digest
report = dict(stage=172, kernel_build=172, release=release, source_sha256=source['source_sha256'],
              checkpatch_pass=True, audio_object_warnings=0, full_build_inherited_eud_warning_only=True,
              image_sha256=sha(image), image_bytes=image.stat().st_size, dtb_sha256=sha(dtb),
              dtb_semantic_changes=[dict(node=p,property=n) for p,n in changes],
              sd1_and_display_sources_preserved=True, config_unchanged=True,
              modules_count=770, module_build_id_only_differences=changed, modules132_runtime_compatible=True,
              initial_dtb_audit_wrong_property_name_corrected=resume,
              firmware_package_and_deployment_pending=True)
for folder in [ref,out]: (folder / 'kernel-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
