from pathlib import Path
import re, tarfile

k=Path('/home/cy122/x2pro-linux/linux')
out=Path('/mnt/e/edk2-samurai-out/kernel76')
def show(path, ranges):
    lines=path.read_text().splitlines()
    print('\n'+str(path))
    for start,end in ranges:
        print('\n'.join(f'{i+1}: {lines[i]}' for i in range(start-1,min(end,len(lines)))))
soc=(k/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text().splitlines()
for i,line in enumerate(soc):
    if re.search(r'i2c@c94000|i2c@884000',line):
        print('\n'.join(f'{j+1}: {soc[j]}' for j in range(i,min(i+32,len(soc)))))
show(out/'stock-sm8150-mtp.dtsi',[(1080,1134)])
show(k/'drivers/power/supply/bq27xxx_battery.c',[(504,528),(839,861),(1290,1308),(1390,1440),(2170,2272)])
show(k/'Documentation/devicetree/bindings/power/supply/bq27xxx.yaml',[(54,121)])
show(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',[(1,65),(325,388)])
archive=Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        if item.isfile() and '/soc/i2c@0xc94000/' in item.name and item.name.count('/')<4:
            print('Live bus prop',item.name,tar.extractfile(item).read().hex())
