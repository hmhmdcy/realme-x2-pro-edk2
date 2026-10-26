from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
s=(HERE/'samurai-usbin-init.c').read_text()
names=['ui_now','ui_clock','ui_snapshot_read','ui_config_read','ui_bit_write','ui_drop_if_safe','ui_work','ui_phase_name','ui_bool','state_show','control_store','ui_stop']
def function(name):
 m=re.search(r'^static (?:const char \*|unsigned long long |ssize_t |int |bool |void )'+name+r'\([^;]*?\)\s*\{',s,re.M)
 assert m,name
 a=m.start();b=s.index('{',a)+1;depth=1
 while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
fs=[function(n) for n in names]
(HERE/'tested-functions.inc').write_text('\n\n'.join(fs)+'\n')
(HERE/'tested-struct.inc').write_text(re.search(r'^struct ui_device \{.*?^\};',s,re.S|re.M).group()+'\n')
(HERE/'function-manifest.json').write_text(json.dumps([dict(name=n,line=s[:s.index(f)].count('\n')+1,sha256=hashlib.sha256(f.encode()).hexdigest()) for n,f in zip(names,fs)],indent=2)+'\n')
