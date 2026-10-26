from pathlib import Path
import ast
import subprocess

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel146')
base=ref.parent / 'kernel145'
for name in ['quiesce-current140.sh','freeze-for-bootloader.sh','enter-bootloader.ps1','enable-transition-eud.ps1']:
    text=(base / name).read_text()
    text=text.replace('kernel145','kernel146').replace('k145','k146').replace('K145','K146')
    text=text.replace("'^#140 '","'^#145 '").replace('dsi-raw-first','ccu-first')
    text=text.replace('python3 /tmp/k146-check-quiesce-state.py --record','python3 /tmp/k146-check-quiesce.py --record')
    text=text.replace('python3 /tmp/k146-check-quiesce-state.py','python3 /tmp/k146-check-quiesce.py')
    path=ref / name.replace('current140','current145')
    assert not path.exists()
    path.write_text(text)
    if path.suffix=='.sh': subprocess.run(['sh','-n',str(path)],check=True)
print('K146_REVIEWED_QUIESCE_FREEZE_F1_TOOLS_ADAPTED_WITH_CURRENT145_GUARDS')
