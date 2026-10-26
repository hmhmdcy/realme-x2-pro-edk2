from pathlib import Path
import ast, tarfile

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel176')
s=(ref/'test-reprobe.py').read_text();marker='def map_paths():'
s=s.replace(marker,'''def supply_counts():
    rows={}
    for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
        fields=line.split()
        if fields and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)',fields[0]):
            rows[fields[0]]=int(fields[1])
    return rows
'''+marker)
s=s.replace('\nmap_read();assert clock_count()==1\n','\nmap_read();assert clock_count()==1\nsupplies_before=supply_counts();assert len(supplies_before)==5 and all(v==1 for v in supplies_before.values())\n')
s=s.replace("        assert clock_count()==0", "        assert clock_count()==0\n        supplies_unbound=supply_counts()\n        if kind=='mfd':assert all(v==0 for v in supplies_unbound.values())\n        else:assert supplies_unbound==supplies_before")
s=s.replace('        wait_card();card=wait_pulse();new_names=map_read();assert clock_count()==1',
'''        wait_card();card=wait_pulse();new_names=map_read();assert clock_count()==1
        supplies_after=supply_counts();assert supplies_after==supplies_before''')
s=s.replace("capture_frames_after_rebind=48000,running_seen=True,pcm_closed=True)",
"capture_frames_after_rebind=48000,running_seen=True,pcm_closed=True,\n                 supplies_unbound=supplies_unbound,supplies_after=supplies_after)")
s=s.replace("no_gain_or_classh_changes=True)","no_gain_or_classh_changes=True,supplies_before=supplies_before,all_supply_consumer_counts_balanced=True)")
ast.parse(s);(ref/'test-reprobe.py').write_text(s)
with tarfile.open(out/'regression-tools-power-private.tar','w') as ar:
    for n in ['test-reprobe.py','test-capture-stop.py','capture-acoustic.py','test-desktop-duplex.py']:ar.add(ref/n,arcname='k176-'+n)
print('K176_REPROBE_POWER_COUNTS_PREPARED',flush=True)
