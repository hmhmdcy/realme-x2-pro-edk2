from pathlib import Path
import hashlib, json, shutil, subprocess
here = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel206')
old = out.parent / 'kernel205'
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source = k / 'drivers/bluetooth/hci_qca.c'
module = k / 'drivers/bluetooth/hci_uart.ko'
assert sha(source) == '7682145e6ec3050c2da5202e2b5e21310a3122f7d8f922669587f5e26e478c6c'
assert sha(old / 'hci_qca-before-diagnostic-private.c') == '645ded4980918a2d0a22dd2d56327bbc69c08e3689e9d313158f0d263e291d90'
check = out / 'restored185-stripped-check-private.ko'
assert not check.exists()
shutil.copyfile(old / 'hci_uart-before-build-private.ko', check)
subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(check)], check=True)
assert sha(check) == 'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
shutil.copyfile(source, out / 'hci_qca-diagnostic-before-restore-private.c')
shutil.copyfile(module, out / 'hci_uart-diagnostic-unstripped-before-restore-private.ko')
shutil.copyfile(old / 'hci_qca-before-diagnostic-private.c', source)
shutil.copyfile(old / 'hci_uart-before-build-private.ko', module)
assert sha(k / '.config') == '55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a'
assert len((k / 'Module.symvers').read_text().splitlines()) == 16793
assert len((k / 'modules.order').read_text().splitlines()) == 770
r = dict(stage=206, original185_hci_qca_source_restored=True, original_unstripped_module_restored=True, stripped_module_matches_phone185=True, diagnostic_source_and_module_preserved=True, config_symbols_order_unchanged=True, source_sha256=sha(source))
(here / 'bluetooth-source-restore-validation.json').write_text(json.dumps(r, indent=2) + '\n')
print(json.dumps(r))
