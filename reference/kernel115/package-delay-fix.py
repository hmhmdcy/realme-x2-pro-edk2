from pathlib import Path
import hashlib,json,subprocess,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel115')
k=Path('/home/cy122/pmos-samurai-kernel115/kernel')
own=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/platform/msm/ipa/ipa_v3/ipahal')
found=[]
for p in own.glob('*.h'):
    for line in p.read_text().splitlines():
        if 'IPA_ENDP_INIT_CTRL_n_ENDP_DELAY_' in line and '#define' in line:
            found.append(dict(source=p.name,line=line))
assert any('BMSK' in r['line'] and '0x2' in r['line'] for r in found)
source=k/'drivers/net/ipa/ipa.ko'
target=out/'ipa-delay-fixed.ko'
shutil.copy2(source,target)
subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(target)],check=True)
magic=subprocess.check_output(['modinfo','-F','vermagic',str(target)],text=True).strip()
assert magic=='7.3.0-rc6-rmx1931-samurai+ SMP preempt mod_unload aarch64'
orig=json.loads((out/'kernel-build-validation.json').read_text())
assert hashlib.sha256((out/'Image-ipa-zram').read_bytes()).hexdigest()==orig['artifact_sha256']['arch/arm64/boot/Image']
report=dict(kernel_build=115,own_delay_bit_verified=True,source_definitions=found,register_offset='0x800',endpoint_stride='0x70',tx_delay_bit=1,rx_suspend_not_supported=True,module_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),vermagic=magic,core_image_unchanged=True,runtime_test_pending=True,goal_complete=False)
(out/'ipa-delay-fix-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
t=(root/'kernel115/quiesce-clean.sh').read_text().replace("'^#113 '","'^#115 '").replace('/var/lib/samurai/k114-final-health/boot-id-private.txt','/var/lib/samurai/k115-first-runtime/boot-id-private.txt')
# Stop the root modem daemon after GUI and NetworkManager users have exited.
needle='/usr/sbin/samurai-bluetooth stop >'
t=t.replace(needle,'''for pid in $(pidof ModemManager || true); do
    test "$(readlink /proc/$pid/exe)" = "$(readlink -f /usr/sbin/ModemManager)"
    kill -TERM "$pid"
done
sleep 1
'''+needle)
(root/'kernel115/quiesce-clean-115.sh').write_text(t)
t=(root/'kernel113/observe-audio-clean-reboot.ps1').read_text().replace('kernel113','kernel115').replace('k113','k115').replace('^#113 ','^#115 ')
(root/'kernel115/observe-audio-clean-reboot.ps1').write_text(t)
print(json.dumps(report,indent=2))
