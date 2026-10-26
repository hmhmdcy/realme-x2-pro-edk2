from pathlib import Path
import ast

ref = Path(__file__).parent
text = (ref.parent / 'kernel170/collect-final.py').read_text()
text = text.replace('k170-', 'k171-').replace('stage=170', 'stage=171')
text = text.replace('k169-final', 'k171-runtime').replace('same_boot_as_k169_final', 'same_boot_as_k171_runtime')
text = text.replace('dmic0-low48-r1', 'dmic0-sd1-low48')
text = text.replace('original_k170', 'original_k171')
text = text.replace('no_kernel_or_firmware_change_in_k170=True', 'kernel168_retained_boot_and_logdump171_deployed=True')
text = text.replace('no_amp_gain_change_in_k170', 'no_amp_gain_change_in_k171')
text = text.replace("log = command(['dmesg'])", """command(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
module_check=command(['sh','-c','cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k171-preflash/old132-module-tree.sha256'])
(out/'module-check-private.txt').write_text(module_check)
log = command(['dmesg'])""")
text = text.replace('report = dict(stage=171,', 'report = dict(stage=171, modules132_verified=True, nv_verified=True,')
ast.parse(text)
assert not (ref / 'collect-final.py').exists()
(ref / 'collect-final.py').write_text(text)
print('K171_FINAL_COLLECTOR_PREPARED')
