from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel297/restore-desktop.py').read_text().replace('stage=297','stage=379').replace('k297-desktop-restore-','k379-desktop-restore-').replace('k297-work','k378-recovered').replace('k297-services-','k379-services-')
(HERE/'restore-desktop.py').write_text(s)
s=(HERE.parent/'kernel297/inspect-ssc-failure.py').read_text().replace('stage=297','stage=379').replace('kernel_build=297','kernel_build=363')
anchor="errors={p:[l for l in t.splitlines() if any(w in l.lower() for w in ['error','fail','timeout','fatal','not permitted'])][-10:] for p,t in d['logs'].items()}"
assert s.count(anchor)==1
s=s.replace(anchor,"errors={word:sum(t.lower().count(word) for t in d['logs'].values()) for word in ['attach','permission denied','not permitted','timeout','fatal']}")
(HERE/'inspect-ssc-failure.py').write_text(s)
health=HERE/'current-health.py';s=health.read_text();anchor="(HERE/'current-health-validation.json').write_text"
assert s.count(anchor)==1
s=s.replace(anchor,"d['camera_ready']=d['services']['greetd']['exit']==0 and all(v==1 for v in d['process_counts'].values()) and d['taint']==0 and all(v=='suspended' for v in d['camera_pm'].values())\n"+anchor);health.write_text(s)
p=HERE/'camera-check.py';s=p.read_text().replace("['healthy'],'Normal SSC/desktop must be ready before creating this capture transaction'","['camera_ready'],'Desktop camera consumers must be ready before creating this capture transaction'");p.write_text(s)
print('Prepared known-failure SSC preservation and normal desktop recovery without DSP reattach.')
