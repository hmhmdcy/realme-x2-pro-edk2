from pathlib import Path

ref = Path(__file__).parent
s = (ref / 'collect-final.py').read_text().replace('k173-final','k173-final-policy')
marker = next(line for line in s.splitlines() if line.startswith('assert sum') and 'module-alsa-card' in line)
s = s.replace(marker,marker+"\nassert sum('\\tmodule-switch-on-port-available\\t' in l for l in module_lines.splitlines()) == 1\nassert 'load-module module-switch-on-port-available' in Path('/etc/pulse/default.pa').read_text()")
s = s.replace('report = dict(stage=173,', 'report = dict(stage=173, live_port_switch_policy_loaded=True, system_startup_policy_command_already_present=True, policy_startup_after_reboot_not_tested=True,')
(ref / 'collect-policy-final.py').write_text(s); compile(s,'collect-policy-final.py','exec')
print('K173_POLICY_FINAL_PREPARED',flush=True)
