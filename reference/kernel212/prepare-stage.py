"""Prepare a fresh, no-flash warm boot after the recorded camera GPU failure."""
from pathlib import Path
import ast,hashlib,json,os,shutil
os.umask(0o077);here=Path(__file__).resolve().parent;previous=here.parent/'kernel211';private=Path('/mnt/e/edk2-samurai-out/kernel212');private.mkdir(mode=0o700)
assert json.loads((previous/'capture-evidence-archive-validation.json').read_text())['private_archive_all_members_verified']
assert json.loads((previous/'cpu-configuration-deployment-validation.json').read_text())['system_libcamera_cpu_configuration_installed']
shutil.copyfile(private.parent/'kernel211/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
(here/'host.py').write_text((previous/'host.py').read_text().replace("Path('/mnt/e/edk2-samurai-out/kernel211')","Path('/mnt/e/edk2-samurai-out/kernel212')"))
(here/'run-native.py').write_bytes((previous/'run-native.py').read_bytes())
guard="""from pathlib import Path
import subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k211-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
warning_log=subprocess.check_output(['dmesg'])
known_warnings=[line for line in warning_log.splitlines() if b'WARNING:' in line]
assert len(known_warnings)==349 and all(b'__arm_lpae_unmap' in line and b'drivers/iommu/io-pgtable-arm.c:673' in line for line in known_warnings)
assert all(warning_log.count(term)==0 for term in [b'Oops:',b'gpu fault:',b'fatal error received',b'Frame reassembly failed'])
"""
(here/'warning-guard.py').write_text(guard)
guard_call="exec(Path('/tmp/k212-warning-guard.py').read_text())"
for name in ['quiesce-current183.sh','stop-gnss-idle.py','quiesce-camera.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','reboot-current.py','fastboot-reboot-current.py','collect-pre-reboot.py','collect-newboot.py','refresh-usb-endpoint.ps1']:
    text=(previous/name).read_text().replace('k211','k212').replace('kernel211','kernel212').replace('stage=211','stage=212').replace("'stage': 211","'stage': 212").replace("['stage'] == 211","['stage'] == 212")
    if name=='collect-pre-reboot.py':
        text=text.replace("root / 'k212-baseline/boot-id-private.txt'","root / 'k211-runtime/boot-id-private.txt'").replace("root / 'k212-module-install/module-tree.sha256'","root / 'k211-module-install/module-tree.sha256'")
        text=text.replace('89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0','c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6')
        text=text.replace("assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'", "assert os.uname().version.startswith('#183 ')\n"+guard_call)
        text=text.replace("assert not any(faults.values()) and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()", "assert faults==dict(warning=349,oops=0,gpu=0,slpi_fatal=0,bluetooth=0) and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()")
        marker="assert all(sha(name) == digest for name, digest in expected.items())"
        text=text.replace(marker,"expected['/etc/libcamera/configuration.yaml']='771c516f85cb3c408e42a561beaa4a4bd56f2db9890c81d40e28468205ecc12e'\n"+marker)
        text=text.replace('same_current210_baseline_boot=True, taint=0, boot210_logdump183_persist_readback_exact=True','same_current211_runtime_boot=True, taint=512, boot211_logdump183_persist_readback_exact=True')
    elif name=='quiesce-current183.sh':
        text=text.replace('test "$(cat /proc/sys/kernel/tainted)" = 0','python3 /tmp/k212-warning-guard.py')
    elif name in ['quiesce-camera.py','disable-crtc.py','check-quiesce.py','linux-restart2-bootloader.py']:
        for statement in ["assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'","assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'"]:
            text=text.replace(statement,guard_call)
        if name=='quiesce-camera.py':text=text.replace('taint=0','taint=512')
        elif name=='disable-crtc.py':text=text.replace("assert log.count('Oops:') == 0 and log.count('WARNING:') == 0", "assert log.count('Oops:') == 0 and log.count('WARNING:') == 349")
        elif name=='check-quiesce.py':
            text=text.replace("current.count('WARNING:')==prior.count('WARNING:')==0","current.count('WARNING:')==prior.count('WARNING:')==349").replace("camera['taint']==0","camera['taint']==512").replace('taint=0','taint=512').replace('known_baseline_gpu_faults=0,','known_baseline_gpu_faults=0,known_gpu_unmap_warnings=349,')
        elif name=='linux-restart2-bootloader.py':text=text.replace('taint=0,','taint=512, known_gpu_unmap_warnings=349,')
    elif name=='reboot-current.py':text=text.replace("proof['taint'] == 0","proof['taint'] == 512 and proof['known_gpu_unmap_warnings'] == 349")
    elif name=='collect-newboot.py':
        text=text.replace("partitions_flashed=['boot']","partitions_flashed=[]")
        text=text.replace("camera_stream_not_started=True,", "camera_stream_not_started=True,same_boot211_image_second_warm_boot=True,")
    if name.endswith('.py'):ast.parse(text,filename=name)
    (here/name).write_text(text)
plan=dict(stage=212,state='Fresh transport prepared. Recorded211 GPU capture failure and all190 native evidence files archived. CPU mode config installed; no212 transition or kernel change yet.',guard='/var/lib/samurai/k211-runtime/boot-id-private.txt',transport='reference/kernel212/host.py',transition_pending=False,next='Fresh current partition/product/module/known-warning audit; orderly quiesce then one guarded no-flash warm reboot. Verify default CPU ISP from configuration on clean boot, actual frames and all resources restored. Keep full peripheral/five-camera goal active.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('212 prepared: current211 guard, exact349 recorded GPU unmap warnings only; no flash planned, no transition sent.')
