from pathlib import Path
import ast
import json

ref = Path(__file__).resolve().parent
build = json.loads((ref / 'build-package-validation.json').read_text())
s = (ref.parent / 'kernel178/test-adsp-restart.py').read_text()
s = s.replace('k178', 'k180').replace('stage=178', 'stage=180').replace('kernel_build=176', 'kernel_build=180')
s = s.replace("startswith('#176 ')", "startswith('#180 ')")
s = s.replace('/var/lib/samurai/k177-final/boot-id-private.txt', '/var/lib/samurai/k180-runtime/boot-id-private.txt')
s = s.replace('6e3ebbe791455ae2c06a2374106f57c1d7ea0aac358191c44d8322b8d50f16cb', build['logdump_sha256'])
s = s.replace("'qmi_wait_timeout': 'QMI wait timeout'}", "'qmi_wait_timeout': 'QMI wait timeout',\n"
              "                'irq_read': 'Failed to read IRQ status', 'irq_config': 'Failed to write config',\n"
              "                'irq_mask': 'Failed to sync masks', 'pdr_listener': 'register listener txn wait failed',\n"
              "                'pdr_missing_state': 'register listener response has no state'}")
s = s.replace("before_log = cmd(['dmesg']);", "start_uptime=float(Path('/proc/uptime').read_text().split()[0])\nbefore_log = cmd(['dmesg']);")
s = s.replace("faults = {k: after_log.count(v)-before_log.count(v) for k, v in patterns.items()}",
              "window='\\n'.join(line for line in after_log.splitlines() if (m:=re.match(r'^\\[\\s*(\\d+\\.\\d+)\\]',line)) and float(m[1])>=start_uptime)\n"
              "    faults = {k: window.count(v) for k, v in patterns.items()}")
s = s.replace('no_kernel_flash_or_machine_rebind=True', 'no_machine_rebind_in_restart_test=True')
ast.parse(s)
(ref / 'test-adsp-restart.py').write_text(s)
print('K180_ADSP_RESTART_TEST_PREPARED')
