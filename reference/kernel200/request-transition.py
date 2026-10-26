from pathlib import Path
import json,host

ref=Path(__file__).resolve().parent
proof=json.loads((host.PRIVATE/'preliminary-quiesce-private.json').read_text())
assert proof['current_kernel']==183 and proof['taint']==512 and proof['preliminary_quiesce_pass']
deploy=json.loads((host.PRIVATE/'paired-module-deployment-private.json').read_text())
assert deploy['module_replaced_for_paired_static_dt_boot']
boot=(host.PRIVATE/'source-boot-id-private.txt').read_text().strip()
assert len(boot)==36 and all(c in '0123456789abcdef-' for c in boot)
marker=host.PRIVATE/'reboot-request-private.json';assert not marker.exists()
# The sole submission is recorded before dispatch. A timeout is never an authorization to repeat.
marker.write_text(json.dumps(dict(source_boot_id=boot,request_count=1,command='bootloader',boot_flash_prepared=True),indent=2)+'\n')
p=host.ssh('test "$(cat /proc/sys/kernel/random/boot_id)" = '+boot+' && nohup sh /var/lib/samurai/k200-reboot-tools/final-transition.sh '+boot+' > /run/k200-transition-private.log 2>&1 < /dev/null &',timeout=12)
(host.PRIVATE/'transition-submit-private.log').write_bytes(p.stdout+p.stderr)
print('K200_SINGLE_DETACHED_TRANSITION_SUBMITTED_VERIFY_FASTBOOT_STATE')
