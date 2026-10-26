from pathlib import Path
ref=Path(__file__).resolve().parent;s=(ref/'probe-pmic-driver-cold.py').read_text()
s=s.replace('k194-pmic-coldprobe','k194-pmic-warmprobe').replace('Exercise normal PM8008 MFD probe from a measured reset-address state.','Exercise normal PM8008 MFD probe from the already-assigned address.')
a=s.index(' line=request(3,8);');b=s.index(" assert run(['insmod',str(stage/'samurai-pmic-fixture.ko')])",a)
s=s[:a]+" report['reset_address4']=read(4,0x100,6);report['reset_address8']=read(8,0x100,6);save()\n"+s[b:]
s=s.replace("assert b'assigned PM8008 primary address 0x04' in after_log[len(before_log):] and not report['writes']","assert b'assigned PM8008 primary address 0x04' not in after_log[len(before_log):] and not report['writes'] and not report['reset_levels']")
s=s.replace('reset_address=8,assigned_address=4','already_assigned_address=4,reset_pulse_needed=False').replace('manual_sid_fallback_needed=False','sid_reassignment_needed=False')
(ref/'probe-pmic-driver-warm.py').write_text(s)
print('Warm probe script generated with no userspace reset or SID write')
