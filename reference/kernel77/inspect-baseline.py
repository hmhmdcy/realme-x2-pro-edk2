"""Read-only audit of the current gauge driver, DT and preserved artifacts."""
from pathlib import Path
import hashlib,json,re,subprocess
k=Path('/home/cy122/x2pro-linux/linux')
r=Path('/home/cy122/edk2-samurai/repo')
ref=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel77')
def show(path,pattern,before=2,after=15):
    lines=path.read_text().splitlines(); indices=set()
    for i,line in enumerate(lines):
        if re.search(pattern,line): indices.update(range(max(0,i-before),min(len(lines),i+after)))
    print('\n'+str(path))
    print('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(indices)))
show(k/'drivers/power/supply/bq27xxx_battery_i2c.c',r'bq27xxx_battery_i2c_(read|write|probe)|bq28z610|bus\.|battery_setup',0,22)
show(k/'drivers/power/supply/bq27xxx_battery.c',r'bq28z610|bq27xxx_battery_settings\(|bq27xxx_battery_setup\(|bus.write|bus.write_bulk|bus.read|unseal|nvmem|set_config',1,12)
show(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi',r'i2c15:|i2c15_default:|i2c1:|gpi_dma2:|qup_opp_table',1,27)
show(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',r'^&(?:i2c|gpi_dma|qupv3|tlmm)',1,18)
paths=[k/'arch/arm64/boot/Image',k/'.config',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',
       r/'boot-samurai.img',r/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb']
facts={str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths}
(out/'baseline-artifact-hashes.json').write_text(json.dumps(facts,indent=2)+'\n')
print('\nARTIFACTS:',json.dumps(facts))
