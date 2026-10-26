from pathlib import Path
import ast,json,subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel153')
base=ref.parent/'kernel152'
out=Path('/mnt/e/edk2-samurai-out/kernel153')
build=json.loads((ref/'build-package-validation.json').read_text())
build['dtb_unchanged']=True
(out/'build-package-validation.json').write_text(json.dumps(build,indent=2)+'\n')
for name in ['collect-preflash.py','quiesce-current147.sh','check-quiesce.py',
    'freeze-for-bootloader.sh','enter-bootloader.ps1','flash-dsi-candidate.ps1',
    'capture-startup.py','k152-startup-trace','capture-display-cycles.py','display-power.py']:
    s=(base/name).read_text().replace('kernel152','kernel153').replace('k152','k153').replace('K152','K153')
    s=s.replace("'#152 '","'#153 '").replace("'^#152 '","'^#153 '")
    s=s.replace("==3","==0").replace('known_baseline_gpu_faults=3','known_baseline_gpu_faults=0')
    s=s.replace('target_kernel=152','target_kernel=153').replace('$q.target_kernel -ne 152','$q.target_kernel -ne 153')
    s=s.replace('stage=152','stage=153').replace('kernel_build=152','kernel_build=153')
    s=s.replace('logdump-k153-dsi-lifecycle.img','logdump-k153-panel-handoff.img').replace('lifecycle-first','gpio-first')
    # The current recovered boot allocated DRM minor zero; the next normal boot
    # recorder must continue to discover the platform card dynamically.
    if name in ['collect-preflash.py','quiesce-current147.sh','check-quiesce.py','freeze-for-bootloader.sh']:
        s=s.replace('/dev/dri/card1','/dev/dri/card0').replace('/sys/kernel/debug/dri/1','/sys/kernel/debug/dri/0')
    if name=='capture-startup.py':
        s=s.replace("state=Path('/sys/kernel/debug/dri/1/state').read_text() if Path('/sys/kernel/debug/dri/1/state').exists() else ''",
            "card=Path('/dev/dri/by-path/platform-ae01000.display-controller-card')\n            state_path=Path('/sys/kernel/debug/dri')/card.resolve().name.removeprefix('card')/'state'\n            state=state_path.read_text() if state_path.exists() else ''")
        s=s.replace("capture(['cat','/sys/kernel/debug/dri/1/state'],'drm-final-private.txt')",
            "card=Path('/dev/dri/by-path/platform-ae01000.display-controller-card').resolve()\n    capture(['cat',str(Path('/sys/kernel/debug/dri')/card.name.removeprefix('card')/'state')],'drm-final-private.txt')")
    dest=ref/name.replace('flash-dsi','flash-gpio').replace('k152-startup','k153-startup')
    assert not dest.exists()
    dest.write_text(s)
    if dest.suffix=='.sh' or name=='k152-startup-trace':subprocess.run(['sh','-n',str(dest)],check=True)
    if dest.suffix=='.py':ast.parse(s)
print('K153_CURRENT147_GUARDED_TOOLS_READY',flush=True)
