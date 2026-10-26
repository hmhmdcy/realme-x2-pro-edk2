from pathlib import Path
import re

root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for filename,names in [('drivers/slimbus/core.c',['slim_register_controller','slim_unregister_controller']),
    ('drivers/slimbus/qcom-ngd-ctrl.c',['slim_pd_status','qcom_slim_ngd_probe','qcom_slim_ngd_remove'])]:
    text=root.joinpath(filename).read_text()
    lines=text.splitlines()
    print(filename)
    for name in names:
        match=re.search(r'^(?:static )?[^;{}]*\b'+name+r'\([^;{}]*\)\n\{',text,re.M)
        if not match:continue
        depth=1;end=match.end()
        while depth:
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        start=text[:match.start()].count('\n')
        for number,line in enumerate(text[match.start():end].splitlines(),start+1):print(f'{number}: {line}')
    for number,line in enumerate(lines,1):
        if re.search(r'slim_register_controller|slim_unregister_controller|SLIMBUS_DEVICE_(DOWN|UP)|ngd_ctrl_probe|ngd_remove',line):
            print(f'REFERENCE {number}: {line}')
