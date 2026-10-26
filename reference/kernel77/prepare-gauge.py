"""Back up the verified baseline and add only the stock-wired gauge node."""
from pathlib import Path
import difflib,gzip,hashlib,json,shutil,subprocess
k=Path('/home/cy122/x2pro-linux/linux'); r=Path('/home/cy122/edk2-samurai/repo')
ref=Path(__file__).resolve().parent; out=Path('/mnt/e/edk2-samurai-out/kernel77')
old=ref.parent/'kernel75'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()=='136157ba0375d7af92e98896008a8566230c8214'
assert not subprocess.check_output(['git','-C',str(r),'status','--porcelain'])
final=json.loads((old/'final-validation.json').read_text())
source=json.loads((old/'final-source-manifest.json').read_text())['sources']
preserved=dict(final['preserved_sources'])
for n,digest in source.items():
    assert sha(k/n)==digest,n
    preserved[n]=digest
for n,digest in final['preserved_sources'].items():
    path=Path('/home/cy122/x2pro-linux/initramfs')/('init' if n=='init' else 'usr/sbin/samurai-usb') if n in ('init','samurai-usb') else k/n
    assert sha(path)==digest,n
config=(k/'.config').read_text()
assert 'CONFIG_BATTERY_BQ27XXX=y' in config and 'CONFIG_BATTERY_BQ27XXX_I2C=y' in config
assert '# CONFIG_BATTERY_BQ27XXX_DT_UPDATES_NVM is not set' in config
assert sha(k/'.config')==final['artifacts']['config-before']['sha256']
assert sha(k/'arch/arm64/boot/Image')==final['artifacts']['Image-final']['sha256']
fv=r/'workspace/Build/samurai/RELEASE_GCC5/FV'
items={'boot-before.img':r/'boot-samurai.img','logdump-before.img':out.parent/'kernel75/logdump-k75-final.img',
       'dts-before':k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
       'firmware-before.dtb':r/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb',
       'compat-before.dtb':r/'Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb',
       'firmware-before.fd':fv/'SM8150_UEFI.fd','fvmain-before.Fv':fv/'FVMAIN.Fv',
       'fvcompact-before.Fv':fv/'FVMAIN_COMPACT.Fv','config-before':k/'.config'}
for name,path in items.items():
    assert not (out/name).exists(),name
    shutil.copyfile(path,out/name)
assert sha(out/'boot-before.img')==final['artifacts']['boot-k75-gpu.img']['sha256']
assert sha(out/'logdump-before.img')==final['artifacts']['logdump-k75-final.img']['sha256']
assert sha(out/'firmware-before.dtb')==final['artifacts']['firmware-after.dtb']['sha256']
(ref/'sources-before.json').write_text(json.dumps(preserved,indent=2)+'\n')
raw=gzip.decompress((out/'before-dmesg.gz').read_bytes())
(out/'before-dmesg.txt').write_bytes(raw)
shutil.copyfile(out/'before-dmesg.gz',ref/'before-dmesg.gz')
(ref/'before-dmesg.txt').write_bytes(raw)
p=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
s=p.read_text(); anchor='&i2c17 {\n'
assert s.count(anchor)==1 and '&i2c15 {' not in s
addition='''/* Stock BQ28Z610 at QUP15: standard read-only battery monitoring. */
&i2c15 {
\tclock-frequency = <100000>;
\tstatus = "okay";

\tfuel-gauge@55 {
\t\tcompatible = "ti,bq28z610";
\t\treg = <0x55>;
\t};
};

'''
p.write_text(s.replace(anchor,addition+anchor))
relative=str(p.relative_to(k))
patch='diff --git a/'+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(s.splitlines(True),p.read_text().splitlines(True),'a/'+relative,'b/'+relative))
(ref/'gauge-dts.patch').write_text(patch)
(ref/'sm8150-samurai.dts.after').write_bytes(p.read_bytes())
print('Verified baseline backed up. Added only i2c15/100kHz and ti,bq28z610@55; no charger node or battery policy.')
