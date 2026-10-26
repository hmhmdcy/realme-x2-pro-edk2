from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');old=r/'reference/kernel128';ref=r/'reference/kernel129'
s=(old/'inspect-runtime.py').read_text().replace('kernel128','kernel129').replace('k128','k129').replace('#128 SMP PREEMPT','#129 SMP PREEMPT').replace('kernel_build=128','kernel_build=129')
s=s.replace('report=dict(',"assert data['console-node.txt']==b'character special file 600 5 1 0 0\\n'\nassert b'unable to open an initial console' not in data['dmesg.txt']\nassert b'Run /init as init process' in data['dmesg.txt']\nreport=dict(initial_console_warning_count=0,live_console_char_5_1_root0600=True,original_init_userspace_reached=True,")
(ref/'inspect-runtime.py').write_text(s)
s=(r/'reference/kernel126/enable-eud.ps1').read_text().replace('kernel126','kernel129').replace('K126','K129').replace('tpg-first','console-node-r2');(ref/'enable-eud.ps1').write_text(s)
s=(old/'collect-final-health.sh').read_text().replace('k128','k129').replace("'^#128 '","'^#129 '").replace('K128','K129')
s=s.replace('dmesg > "$dest/dmesg-after.txt"','stat -c "%F %a %t %T %u %g" /dev/console > "$dest/console-node.txt"\ndmesg > "$dest/dmesg-after.txt"')
(ref/'collect-final-health.sh').write_text(s)
s=(old/'verify-final-health.py').read_text().replace('kernel128','kernel129').replace('current_kernel=128','current_kernel=129')
s=s.replace('log=after.decode();report=dict(',"assert data['console-node.txt']==b'character special file 600 5 1 0 0\\n'\nassert b'unable to open an initial console' not in before and b'unable to open an initial console' not in after\nlog=after.decode();report=dict(console_warning_resolved=True,")
(ref/'verify-final-health.py').write_text(s)
print('K129_CONSOLE_RUNTIME_AND_FINAL_HEALTH_OBSERVATION_TOOLS_PREPARED',flush=True)
