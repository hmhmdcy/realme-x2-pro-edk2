from pathlib import Path
import json,re
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel210/source-before')
names=json.loads((out/'source-file-hashes-private.json').read_text())
print(json.dumps(dict(modified_source_names=list(names))))
recipe=k/'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd'
print(json.dumps(dict(dtb_command=recipe.read_text().splitlines()[0] if recipe.exists() else None)))
p=k/'drivers/media/i2c/Kconfig';text=p.read_text();blocks=[]
for match in re.finditer(r'^config VIDEO_IMX471\s*$',text,re.M):
    end=text.find('\nconfig ',match.end());blocks.append(text[match.start():end if end>=0 else len(text)])
print(json.dumps(dict(imx471_kconfig_definitions=len(blocks),definitions=blocks)))
for file in ['arch/arm64/boot/dts/qcom/sm8150-samurai.dts','arch/arm64/boot/dts/qcom/sm8150-mtp.dts','arch/arm64/boot/dts/qcom/sm8150.dtsi']:
    lines=(k/file).read_text().splitlines();indices=set()
    for i,line in enumerate(lines):
        if any(word in line for word in ['&camss','&cci1','&i2c1 ','vreg_l1c_1p8:','vreg_s8c_1p3:','pm8008']):indices.update(range(max(0,i-2),min(len(lines),i+25)))
    if indices:print(json.dumps(dict(file=file,lines=[dict(line=i+1,text=lines[i]) for i in sorted(indices) if not any(word in lines[i].lower() for word in ['bd-address','mac-address','serial-number'])])))
