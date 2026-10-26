from pathlib import Path
import difflib
import hashlib
import json
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel185')
path = k / 'drivers/bluetooth/hci_qca.c'
text = path.read_text()
text = text.replace('test_bit(QCA_POWER_PULSE, &qca->flags) && !qca->rx_skb)',
                    'test_bit(QCA_POWER_PULSE, &qca->flags) &&\n\t    !qca->rx_skb && !hu->padding)')
text = text.replace('if (ret != sizeof(cmd))', 'if (ret != 1)')
path.write_text(text)
before = (out / 'hci_qca-before-private.c').read_text()
body = ''.join(difflib.unified_diff(before.splitlines(True), text.splitlines(True),
                                 fromfile='a/drivers/bluetooth/hci_qca.c', tofile='b/drivers/bluetooth/hci_qca.c'))
intro = '''Subject: [PATCH] Bluetooth: qca: separate power-pulse NUL prefixes from H4

WCN399x power-on/off uses a raw UART pulse before reopening the port for
HCI. On RMX1931 the pulse interval produces one unframed NUL, which was
sent to the H4 parser and returned EILSEQ. Keep a finite pulse window,
count and consume leading NULs only when no frame or padding is pending.
Normal H4 input and unexpected bytes still use the existing parser.

Also reject a zero-byte pulse write and restore flow control on failure.
The controller boot/shutdown delays and packet-mode error paths remain.

---

'''
(ref / 'qca-power-pulse-rx.patch').write_text(intro + 'diff --git a/drivers/bluetooth/hci_qca.c b/drivers/bluetooth/hci_qca.c\n' + body)
subprocess.run(['git', 'diff', '--check'], cwd=k, check=True)
result = subprocess.run(['perl', 'scripts/checkpatch.pl', '--no-signoff', '--strict', str(ref / 'qca-power-pulse-rx.patch')],
                        cwd=k, capture_output=True)
(out / 'checkpatch-final-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads((ref / 'source-validation.json').read_text())
report.update(source_sha256_after=hashlib.sha256(text.encode()).hexdigest(),
              checkpatch_exit=result.returncode, unsigned_local_patch_no_signoff=True,
              pending_h4_padding_preserved=True)
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
assert result.returncode == 0
