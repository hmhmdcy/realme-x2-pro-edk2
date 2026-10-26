from pathlib import Path
import json,re
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel210')
board=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
lines=board.read_text().splitlines()
print(json.dumps(dict(board_lines=len(lines),camera_related_lines=[dict(line=i+1,text=line) for i,line in enumerate(lines) if any(word in line.lower() for word in ['camss','cci','pm8008','vreg_l1c','vreg_s8c','camcc'])])))
for name in ['arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd','drivers/media/v4l2-core/Kconfig','drivers/media/v4l2-core/Makefile','drivers/media/i2c/Kconfig']:
    p=k/name
    if not p.exists():continue
    lines=p.read_text().splitlines();result=[]
    for i,line in enumerate(lines):
        if (name.endswith('.cmd') and line.startswith('cmd_')) or (not name.endswith('.cmd') and any(word in line for word in ['CCI','IMX471'])):
            result.extend(lines[max(0,i-1):min(len(lines),i+9)])
    print(json.dumps(dict(path=name,matching_lines=result)))
print(json.dumps(dict(core_cci_exists=(k/'drivers/media/v4l2-core/v4l2-cci.c').exists(),core_cci_header_exists=(k/'include/media/v4l2-cci.h').exists())))
