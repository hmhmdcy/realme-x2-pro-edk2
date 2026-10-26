from pathlib import Path
import ast,subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel154')
base=ref.parent/'kernel153'
for name in ['collect-preflash.py','quiesce-current147.sh','check-quiesce.py','freeze-for-bootloader.sh',
    'enter-bootloader.ps1','flash-gpio-candidate.ps1','poll-first-boot.ps1','capture-startup.py',
    'k153-startup-trace','capture-display-cycles.py','display-power.py','verify-runtime.py']:
    text=(base/name).read_text().replace('kernel153','kernel154').replace('k153','k154').replace('K153','K154')
    text=text.replace("'#153 '","'#154 '").replace("'^#153 '","'^#154 '")
    text=text.replace('kernel_build=153','kernel_build=154')
    text=text.replace('stage=153','stage=154').replace('target_kernel=153','target_kernel=154')
    text=text.replace('$q.target_kernel -ne 153','$q.target_kernel -ne 154')
    text=text.replace('$q.current_kernel -ne 147','$q.current_kernel -ne 153')
    text=text.replace("'#153 *'","'#154 *'").replace('New153','New154')
    text=text.replace('logdump-k154-panel-handoff.img','logdump-k154-host-init.img').replace('gpio-first','host-init-first')
    if name in ['collect-preflash.py','quiesce-current147.sh','check-quiesce.py','freeze-for-bootloader.sh']:
        text=text.replace("'#147 '","'#153 '").replace("'^#147 '","'^#153 '")
        text=text.replace('current_kernel=147','current_kernel=153')
        text=text.replace('/dev/dri/card0','/dev/dri/card1').replace('/sys/kernel/debug/dri/0','/sys/kernel/debug/dri/1')
    text=text.replace('CURRENT147','CURRENT153').replace('CURRENT140','CURRENT153').replace('CURRENT145','CURRENT153')
    dest=ref/name.replace('quiesce-current147','quiesce-current153').replace('flash-gpio','flash-host-init').replace('k153-startup','k154-startup')
    assert not dest.exists(),dest
    dest.write_text(text)
    if dest.suffix=='.py':ast.parse(text)
    if dest.suffix=='.sh' or name=='k153-startup-trace':subprocess.run(['sh','-n',str(dest)],check=True)
print('K154_DEPLOYMENT_TOOLS_PREPARED')
