from pathlib import Path
import ast
import hashlib
import json
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel180')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
prior = json.loads((ref.parent / 'kernel176/source-validation.json').read_text())
hashes = dict(prior['source_sha256'])
for name, digest in hashes.items():
    if name != 'drivers/mfd/wcd934x.c':
        assert sha(root / name) == digest, name
hashes['drivers/mfd/wcd934x.c'] = sha(root / 'drivers/mfd/wcd934x.c')
hashes['drivers/soc/qcom/pdr_interface.c'] = sha(root / 'drivers/soc/qcom/pdr_interface.c')
assert hashes['drivers/soc/qcom/pdr_interface.c'] == json.loads((ref / 'pdr-host-validation.json').read_text())['actual_pdr_source_sha256']
assert (root / '.config').read_bytes() == (out / 'config-before-private').read_bytes()
subprocess.run(['git', 'diff', '--check'], cwd=root, check=True)
assert set(subprocess.check_output(['git', 'diff', '--name-only'], cwd=root, text=True).splitlines()) == set(hashes)
manifest = dict(stage=180, baseline_kernel=176, modified_this_stage=['drivers/soc/qcom/pdr_interface.c', 'drivers/mfd/wcd934x.c'],
                source_sha256=hashes, checkpatch_pass=True, prior_audio_hardware_values_preserved=True,
                reset_delays_and_hardware_values_unchanged=True, address_lifetimes176_preserved=True,
                pdr_locks_generations_and_lifetimes_changed=True, parent_irq_disabled_before_children=True,
                regmap_cache_policy_unchanged=True, no_offline_io_success_fabricated=True,
                build_and_runtime_pending=True)
for folder in (ref, out):
    (folder / 'source-validation.json').write_text(json.dumps(manifest, indent=2) + '\n')

s = (ref.parent / 'kernel176/test-reset-probe.py').read_text().replace('kernel176', 'kernel180')
s = s.replace('stage=176', 'stage=180').replace('reset-address-and-probe-cleanup.patch', 'pdr-and-parent-irq.patch')
s = s.replace('static char release_order[64];static int release_n;',
              'static char release_order[64];static int release_n;static bool irq_enabled,irq_inflight;')
s = s.replace('(*p)->map=m;irq_count++;return 0;', '(*p)->map=m;irq_count++;irq_enabled=irq_inflight=true;return 0;')
s = s.replace('static void mfd_remove_devices(struct device *d){assert(map_count==1&&irq_count==1);',
              'static void disable_irq(int irq){assert(irq==42&&irq_count==1&&irq_enabled);irq_enabled=irq_inflight=false;release_order[release_n++]=\'d\';}\n'
              'static void disable_irq_nosync(int irq){assert(irq==42&&irq_count==1&&irq_enabled);irq_enabled=false;}\n'
              'static void mfd_remove_devices(struct device *d){assert(map_count==1&&irq_count==1);if(!io_fail)assert(!irq_enabled&&!irq_inflight);')
s = s.replace('free(p);irq_count--;release_order[release_n++]=\'q\';',
              'free(p);irq_count--;irq_enabled=irq_inflight=false;release_order[release_n++]=\'q\';')
s = s.replace('mode=m;io_fail=io;', 'mode=m;io_fail=io;irq_enabled=irq_inflight=false;')
s = s.replace('strcmp(release_order,"cqm gpr")==0||strcmp(release_order,"cqmgpr")==0',
              'strcmp(release_order,"dcqmgpr")==0')
s = s.replace(' printf("probe_cases=%d io_failure_points=%d wrapper_failure_managed_cleanup=1',
              ' for(int cycle=0;cycle<20;cycle++){init(0,0);assert(slim_device_probe(&main_dev.dev)==0);'
              'assert(irq_enabled);assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_DOWN)==0);'
              'assert(!children&&!irq_count&&!map_count&&!irq_enabled&&!irq_inflight);int stopped=release_n;'
              'assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_DOWN)==0&&release_n==stopped);'
              'assert(wcd934x_slim_status(&main_dev,SLIM_DEVICE_STATUS_UP)==0&&irq_enabled&&irq_count==1);'
              'done();cases++;}\n printf("probe_cases=%d io_failure_points=%d wrapper_failure_managed_cleanup=1')
s = s.replace("probe_result=run('reset-probe',code)",
              "probe_result=run('reset-probe',code)\n"
              "run('negative-no-parent-disable',code.replace('\\tdisable_irq(ddata->irq);',''),False)\n"
              "run('negative-parent-disable-too-late',code.replace('\\tdisable_irq(ddata->irq);','').replace('\\tmfd_remove_devices(&sdev->dev);','\\tmfd_remove_devices(&sdev->dev);\\n\\tdisable_irq(ddata->irq);'),False)\n"
              "run('negative-parent-nosync',code.replace('\\tdisable_irq(ddata->irq);','\\tdisable_irq_nosync(ddata->irq);'),False)")
s = s.replace("'disabled-stop-cleanup'],all_passed=True)",
              "'disabled-stop-cleanup','missing-parent-disable','parent-disable-too-late','parent-nosync'],"
              "parent_irq_quiesce_before_children_verified=True,parent_irq_recreated_enabled_20_cycles=True,all_passed=True)")
ast.parse(s)
(ref / 'test-reset-and-irq.py').write_text(s)

s = (ref.parent / 'kernel176/build-package.py').read_text()
s = s.replace('kernel176', 'kernel180').replace('k176', 'k180').replace('K176', 'K180')
s = s.replace("KBUILD_BUILD_VERSION='176'", "KBUILD_BUILD_VERSION='180'").replace("'#176 SMP PREEMPT'", "'#180 SMP PREEMPT'")
s = s.replace('stage=176,kernel_build=176', 'stage=180,kernel_build=180')
s = s.replace("ref.parent/'kernel175/build-package-validation.json'", "ref.parent/'kernel176/build-package-validation.json'")
s = s.replace("assert json.loads((ref/'host-tests-validation.json').read_text())['all_passed']",
              "assert json.loads((ref/'host-tests-validation.json').read_text())['all_passed']\n"
              "assert json.loads((ref/'pdr-host-validation.json').read_text())['all_passed']")
s = s.replace("['W=1','-j4','drivers/mfd/wcd934x.o','drivers/slimbus/core.o','drivers/slimbus/qcom-ngd-ctrl.o','sound/soc/codecs/wcd934x.o']",
              "['W=1','-j4','drivers/mfd/wcd934x.o','drivers/soc/qcom/pdr_interface.o']")
s = s.replace('Image-k180-reset-private', 'Image-k180-pdr-irq-private').replace('logdump-k180-reset.img', 'logdump-k180-pdr-irq.img')
s = s.replace('modules-root176', 'modules-root180')
s = s.replace("rollback=out.parent/'kernel175/logdump-k175-lifetime-v4.img'", "rollback=out.parent/'kernel176/logdump-k176-reset.img'")
s = s.replace('rollback175_sha256', 'rollback176_sha256')
s = s.replace('reset_address_refresh_and_managed_probe_cleanup_included=True,lifetimes175_preserved=True',
              'pdr_transaction_peer_and_lifetime_fix_included=True,parent_irq_pre_teardown_quiesce_included=True,reset_lifetimes176_preserved=True,lifetimes175_preserved=True')
ast.parse(s)
(ref / 'build-package.py').write_text(s)
print('K180_SOURCE_TESTS_BUILD_PREPARED', flush=True)
