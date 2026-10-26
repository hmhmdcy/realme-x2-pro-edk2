"""Reuse closeout checks and inspect only this stage's known worker handles."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel384/close-current.py').read_text().replace('stage=384','stage=385').replace('stage=384','stage=385').replace('k384-boot-r1','k385-boot-r4')
s=s.replace('latest_hardware_experiment_stage=384','latest_hardware_experiment_stage=385')
anchor='runtime_payload_names=sorted'
insert="""worker_handles=[dict(root=str(root),worker_live=live(root,False),collector_live=live(root,True)) for root in [Path('/var/lib/samurai/k385-boot-r'+str(i)) for i in range(1,5)]],
 """
assert anchor in s;s=s.replace(anchor,insert+anchor)
anchor='print(json.dumps(dict(taint='
functions="""def live(root,collector):
 state=json.loads((root/'state.json').read_text());pid=state.get('collector_pid' if collector else 'pid',-1);p=Path('/proc')/str(pid)
 try:return str(root/('snapshot-collector.py' if collector else 'worker.py')).encode() in (p/'cmdline').read_bytes() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 except OSError:return False
"""
assert anchor in s;s=s.replace(anchor,functions+anchor)
s=s.replace("assert not any('stripe' in n or 'iq' in n for n in d['runtime_payload_names'])","assert not any('stripe' in n or 'iq' in n for n in d['runtime_payload_names'])\nassert not any(v['worker_live'] or v['collector_live'] for v in d['worker_handles'])")
exec(compile(s,str(HERE/'close-current-generated.py'),'exec'),globals())
