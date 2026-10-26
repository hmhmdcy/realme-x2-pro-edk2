from pathlib import Path
import hashlib, json, re, subprocess, tarfile

ref=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel76')
kernel=Path('/home/cy122/x2pro-linux/linux')
vendor=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
assert vendor.exists()
def git(*args):
    return subprocess.check_output(['git','--git-dir='+str(vendor),*args])
commit=git('rev-parse','HEAD').decode().strip()
print('Stock commit:',commit)
paths=git('ls-tree','-r','--name-only',commit).decode().splitlines()
selected=[p for p in paths if re.search(r'mp2650|bq27541|bq28z610|bq27.*gauge|gauge.*bq',p,re.I)]
print('Gauge/charger source paths:',json.dumps(selected,indent=2))
manifest={}
for n in selected+['arch/arm64/boot/dts/19781/sm8150-mtp.dtsi','arch/arm64/boot/dts/19781/sm8150-qupv3.dtsi']:
    raw=git('cat-file','-p',commit+':'+n)
    dest=out/('stock-'+Path(n).name)
    dest.write_bytes(raw)
    manifest[n]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    lines=raw.decode(errors='replace').splitlines()
    print('\nSOURCE',n)
    needles=r'mp2650|bq27541|bq28z610|battery|gauge|charger' if n.endswith('.dtsi') else r'DEVICE_TYPE|device_type|BQ28|BQ27541|of_device_id|compatible|i2c_probe|REG.*(TEMP|VOLT|CURR|SOC|FLAGS)'
    wanted=set()
    for i,line in enumerate(lines):
        if re.search(needles,line,re.I):wanted.update(range(max(0,i-3),min(len(lines),i+7)))
    print('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(wanted))[:21000])
(ref/'stock-source-manifest.json').write_text(json.dumps(dict(commit=commit,files=manifest),indent=2)+'\n')
for n in ('drivers/power/supply/bq27xxx_battery_i2c.c','drivers/power/supply/bq27xxx_battery.c',
          'Documentation/devicetree/bindings/power/supply/bq27xxx.yaml','.config'):
    p=kernel/n
    if not p.exists():continue
    lines=p.read_text().splitlines()
    needles=r'BQ28|BQ27541|bq28|bq27541|of_device_id|probe|BATTERY_BQ|CHARGER_MP|QCOM_BATTMGR|QCOM_SMB'
    wanted=set()
    for i,line in enumerate(lines):
        if re.search(needles,line):wanted.update(range(max(0,i-2),min(len(lines),i+5)))
    print('\nMAINLINE',n,'\n'+'\n'.join(f'{i+1}: {lines[i]}' for i in sorted(wanted))[:14000])
archive=Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
if archive.exists():
    matches={}
    with tarfile.open(archive) as tar:
        for item in tar.getmembers():
            if not item.isfile() or not re.search(r'bq27|bq28|mp2650|oplus.*charg|oppo.*charg',item.name,re.I):continue
            raw=tar.extractfile(item).read()
            matches[item.name]=dict(bytes=len(raw),hex=raw.hex(),text=raw.rstrip(b'\0').decode(errors='replace'))
    (ref/'stock-live-power-properties.json').write_text(json.dumps(matches,ensure_ascii=False,indent=2)+'\n')
    print('Live power props:',json.dumps(matches,ensure_ascii=False,indent=2)[:14000])
print('Local WSL remains live:',Path('/proc/uptime').read_text().strip())
