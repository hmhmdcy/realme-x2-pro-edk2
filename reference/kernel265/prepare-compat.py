"""Prepare existing natural-release multi-client fixtures for isolated stage265 candidates."""
from pathlib import Path
R=Path(__file__).parent;B=R.parent/'kernel264'
s=(B/'advanced-probe.py').read_text().replace('/var/lib/samurai/k264-candidate/','/var/lib/samurai/k265-candidate/')
(R/'compat-probe.py').write_text(s)
s=(B/'system-runner.py').read_text().replace("list(range(6000070,6000075))+list(range(6000080,6000085))","list(range(6000090,6000095))")
s=s.replace('scenario=mode-10 if mode>=6000080 else mode','scenario=mode-20')
s=s.replace('/var/lib/samurai/k264-user','/var/lib/samurai/k265-user').replace('/var/lib/samurai/k264-tools','/var/lib/samurai/k265-compat-tools')
s=s.replace("K264_SYSTEM_PLUGIN='1'","K264_SYSTEM_PLUGIN='0',GST_PLUGIN_PATH='/var/lib/samurai/k265-candidate',LD_LIBRARY_PATH='/var/lib/samurai/k265-candidate'")
s=s.replace("'advanced-probe.py'","'compat-probe.py'").replace("str(tools/'native-stream-probe')","'/var/lib/samurai/k264-tools/native-stream-probe'")
s=s.replace("r['source_plugin']=='/usr/lib/gstreamer-1.0/libgstpipewire.so'","r['source_plugin']=='/var/lib/samurai/k265-candidate/libgstpipewire.so'")
s=s.replace('candidate_library_overrides=False','candidate_library_overrides=True')
(R/'compat-runner.py').write_text(s)
s=(B/'native-system-natural.py').read_text().replace('delay in range(6000080,6000085)','delay in range(6000090,6000095)')
s=s.replace("out=root/('k264-pipewire-'+str(delay)+'-r2')","out=root/('k265-compat-'+str(delay))")
s=s.replace("'/var/lib/samurai/k264-tools/system-runner.py'","'/var/lib/samurai/k265-compat-tools/compat-runner.py'")
s=s.replace("instances/k264_pipewire","instances/k265_compat")
s=s.replace('stage=264','stage=265').replace('delay==6000084','delay==6000094').replace('delay!=6000084','delay!=6000094')
(R/'native-compat.py').write_text(s)
(R/'select-front.py').write_bytes((B/'select-front.py').read_bytes())
print('Prepared distinct candidate multi-client contexts')

