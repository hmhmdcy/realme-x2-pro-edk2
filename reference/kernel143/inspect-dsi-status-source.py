from pathlib import Path
root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
paths=['drivers/gpu/drm/msm/dsi/dsi_host.c','drivers/gpu/drm/msm/registers/display/dsi.xml','drivers/gpu/drm/msm/registers/display/dsi.xml.h']
for name in paths:
    path=root/name
    if not path.exists():continue
    lines=path.read_text().splitlines()
    indices=[i for i,line in enumerate(lines) if any(x in line for x in ['static void dsi_err_worker','DSI_ERR_STATE_', 'err_work_state =', 'err_work_state |='])]
    selected=set()
    for index in indices:
        selected.update(range(max(0,index-2),min(len(lines),index+(55 if 'static void dsi_err_worker' in lines[index] else 7))))
    print(name)
    for i in sorted(selected):print(f'{i+1}: {lines[i]}')
