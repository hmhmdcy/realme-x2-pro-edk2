"""Create the narrow standalone worker from the frozen R8 transaction; no device I/O."""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
base = ROOT / 'reference/charging-oem-audit-20261023/r8-update/update-r8.py'
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '479916c260c7ee9c654ba6471ec22f3ece67d5d797d2de03d5d5e199ee80814b'
text = raw.decode().split("if __name__ == '__main__':")[0]
text = text.replace('class Device:', 'class R8Device:')
text = text.replace("'transaction': 'charging-update-r8'", "'transaction_id': request['transaction_id'], 'schema': 'samurai-charger-reattach-update-result-v1'")
text = text.replace("        healthy(before, allow_full=False)\n        need(before['limits']['native_ua'] == before['limits']['source_budget_ua'] == before['limits']['input_ua'] == 100000\n             and '[SDP]' in before['source']['usb_type'], 'current real SDP native/effective/physical baseline 100mA')", "        result['before_state'] = healthy(before, allow_full=True)\n        need(result['before_state'] == 'managed', 'Full state cannot be restored by the existing API; no stop/unload')")
text = text.replace("        phase = 'old-stop'\n", "        phase = 'old-stop'\n        continuity(before, io.observe(manager), allow_full=False)\n")
text = text.replace("        safe_sample(old_paused)  # stop must not conceal a fault acquired since preflight", "        continuity(before, old_paused, allow_full=False)  # preserve Full, faults and budget history")
text = text.replace("        phase = 'new-inhibited-sample'", "        io.cap_inhibited(before)\n        phase = 'new-inhibited-sample'")
text = text.replace("        result['new_inhibited_sample'] = io.inhibited_ready(manager, request)['sample']", "        new_paused = io.inhibited_ready(manager, request)\n        result['new_inhibited_sample'] = new_paused['sample']\n        io.log('new-inhibited-private.json', new_paused)")
text = text.replace("        result['accepted_state'] = healthy(after, allow_full=True)", "        io.log('after-private.json', after)\n        result['accepted_state'] = healthy(after, allow_full=True)")
text = text.replace("        result['old_stopped_sample'] = old_paused['sample']", "        result['old_stopped_sample'] = old_paused['sample']\n        io.log('old-inhibited-private.json', old_paused)")
text = text.replace("    phase = 'request'", "    result['request_sha256'] = sha(io.request_raw)\n    phase = 'request'")
text = text.replace("        need(after['limits'] == before['limits'], 'NORMAL SDP100 input/charge/CV/effective budget must match r7 exactly')", "        need(after['limits'] == before['limits'], 'input/charge/CV/native/effective budget must remain exact')")
text = text.replace("                        safe_sample(current)\n", "                        continuity(before, current, allow_full=False)\n")
text = text.replace("                    io.notes_match(manager, old)\n                    result['restored_inhibited_sample']", "                    io.notes_match(manager, old)\n                    io.cap_inhibited(before)\n                    result['restored_inhibited_sample']")
text = text.replace("        try:\n            io.finish(result)\n        finally:\n            io.close()", "        try:\n            io.close()\n        except Exception as close_error:\n            result['close_error'] = detail(close_error)\n            result['passed'] = False\n        io.finish(result)")
text = text.replace("<= 2000000", "<= 3000000")
text = text.replace("        self.child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)", "        self.child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)")
text = text.replace("        self.log('last-process-private.json'", "        self.child.wait()\n        self.log('last-process-private.json'")
text = text.replace("        temp = p.with_name(p.name + '.r8-next')", "        temp = p.with_name(p.name + '.reattach-next')")
for old_label, new_label in [('installed r7 manifest hash', 'installed IRQ baseline manifest hash'),
                             ('fresh restored r7 service verify', 'fresh restored IRQ baseline service verify'),
                             ('r7-managed-current-source-budget', 'irq-baseline-managed-current-source-budget'),
                             ('r7-files-and-module-retained', 'irq-baseline-files-and-module-retained'),
                             ('r7 disk repair only', 'IRQ baseline disk repair only')]:
    text = text.replace(old_label, new_label)
# Definitions below replace only the old R7 binding / new observation guards.
text += '\n' + (HERE / 'worker-delta.py.inc').read_text()
(HERE / 'stage-worker.py').write_text(text, encoding='utf-8', newline='\n')
print(hashlib.sha256((HERE / 'stage-worker.py').read_bytes()).hexdigest())
