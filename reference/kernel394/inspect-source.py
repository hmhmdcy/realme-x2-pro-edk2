from pathlib import Path
import importlib.util,re
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';p=source/'drivers/media/platform/qcom/camss';s=(p/'camss-icp-a5-boot.c').read_text()
print(s[:1800])
for name in ['parse_message','process_message','command_failure','camss_a5_stop']:
 m=re.search(r'(?:static )?(?:bool|void|int|irqreturn_t)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',s,re.S|re.M)
 if m:print(m.group())
for i,l in enumerate(s.splitlines()):
 if 'complete(' in l or 'static irqreturn_t' in l:print(i+1,l)
start=s.index('static irqreturn_t');print(s[start:start+5800])
print('FAULT CONFIG:',*[l for l in (source.parent/'build/.config').read_text().splitlines() if any(x in l for x in ['FAULT_INJECTION','KPROBE_EVENTS','FAIL_FUNCTION'])],sep='\n')
