"""Back up verified session77 artifacts and enable only the stock QUP1 bus."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel79')
k = Path('/home/cy122/x2pro-linux/linux')
r = Path('/home/cy122/edk2-samurai/repo')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(['git', '-C', str(r), 'rev-parse', 'HEAD'], text=True).strip() == '3dd07f48513c3c1b949dd8d911bb0bf7c84f7c96'
assert not subprocess.check_output(['git', '-C', str(r), 'status', '--porcelain'])
baseline = json.loads((ref.parent / 'kernel78/unchanged-artifacts-validation.json').read_text())
assert sha(k/'arch/arm64/boot/Image') == baseline['kernel_image_sha256']
assert sha(k/'.config') == baseline['config_sha256']
assert sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb') == baseline['dtb_sha256']
preserved = json.loads((ref.parent/'kernel77/sources-before.json').read_text())
preserved['arch/arm64/boot/dts/qcom/sm8150-samurai.dts'] = sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts')
for name, digest in preserved.items():
    p = Path('/home/cy122/x2pro-linux/initramfs') / ('init' if name == 'init' else 'usr/sbin/samurai-usb') if name in ('init','samurai-usb') else k/name
    assert sha(p) == digest, name
fv = r/'workspace/Build/samurai/RELEASE_GCC5/FV'
items = {'boot-before.img':r/'boot-samurai.img',
         'logdump-before.img':out.parent/'kernel75/logdump-k75-final.img',
         'dts-before':k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
         'firmware-before.dtb':r/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb',
         'compat-before.dtb':r/'Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb',
         'firmware-before.fd':fv/'SM8150_UEFI.fd','fvmain-before.Fv':fv/'FVMAIN.Fv',
         'fvcompact-before.Fv':fv/'FVMAIN_COMPACT.Fv','config-before':k/'.config'}
for name, p in items.items():
    assert not (out/name).exists(), name
    shutil.copyfile(p, out/name)
assert sha(out/'boot-before.img') == '3fbbd0eecf7e793f97920d55bd9ec2a30329d6e53edb307200160a23e1de923e'
assert sha(out/'logdump-before.img') == '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0'
(ref/'sources-before.json').write_text(json.dumps(preserved, indent=2)+'\n')
p = k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
s = p.read_text()
anchor = '/* Stock BQ28Z610 at QUP15: standard read-only battery monitoring. */\n'
assert s.count(anchor) == 1
assert '&i2c1 {' not in s and '&qupv3_id_0 {' not in s and '&gpi_dma0 {' not in s
addition = '''/* Stock QUP1 wiring; no charger client or charging policy is bound. */
&gpi_dma0 {
\tstatus = "okay";
};

&qupv3_id_0 {
\tstatus = "okay";
};

&i2c1 {
\tclock-frequency = <400000>;
\tstatus = "okay";
};

'''
p.write_text(s.replace(anchor, addition+anchor))
relative = str(p.relative_to(k))
patch = 'diff --git a/'+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(s.splitlines(True),p.read_text().splitlines(True),'a/'+relative,'b/'+relative))
(ref/'bus-dts.patch').write_text(patch)
(ref/'sm8150-samurai.dts.after').write_bytes(p.read_bytes())
print('Backed up current gauge/display baseline; changed only GPI0/QUP0/QUP1 bus status and 400kHz.')
