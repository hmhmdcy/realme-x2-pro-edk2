from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;T=storage.candidate()/'src/libcamera-v0.7.2';p=T/'src/ipa/camss-vfe/ipe_tone_profile.cpp';t=p.read_text()
for a,b in [('auto enabled=gtm["enabled"].get<bool>();','auto gtmEnabled=gtm["enabled"].get<bool>();'),('!gtm.isDictionary() || !enabled ||','!gtm.isDictionary() || !gtmEnabled ||'),('gtm["manual_curve"].get<uint32_t>(2)!=0','gtm["manual_curve"].get<uint32_t>(2)>1 || gtm["v2_enable"].get<uint32_t>(2)>1'),('if(*enabled && (!p.tmcEnabled_','if(*gtmEnabled && (!p.tmcEnabled_'),('p.gtmEnabled_=*enabled;','p.gtmEnabled_=*gtmEnabled;')]:
 assert t.count(a)==1,(a,t.count(a));t=t.replace(a,b)
p.write_text(t);s=json.loads((HERE/'source-state.json').read_text())
for r in s['source_hashes']:r['sha256']=hashlib.sha256((T/r['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
