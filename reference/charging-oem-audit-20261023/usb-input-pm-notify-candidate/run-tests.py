from pathlib import Path
import hashlib,json,os,re,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/usb-input-pm-notify-tests-03')
assert not OUT.exists();OUT.mkdir(mode=0o700)
source=(HERE/'samurai-usb-input.c').read_text()
old=(HERE.parent/'usb-input-irq-native-pm-link-candidate/samurai-usb-input.c').read_text()
def function(text,name):
    match=re.search(r'^static [^\n]+\b'+name+r'\(',text,re.M);assert match,name
    start=match.start();brace=text.index('{',match.end());depth=1;pos=brace+1
    while depth:
        if text[pos]=='{':depth+=1
        if text[pos]=='}':depth-=1
        pos+=1
    return text[start:pos]
names=['samurai_usb_changed','samurai_usb_set_property','samurai_usb_poll','samurai_usb_stop','samurai_usb_suspend','samurai_usb_resume','samurai_usb_prepare','samurai_usb_complete','samurai_usb_event']
(OUT/'actual-functions.inc').write_text('\n\n'.join(function(source,name) for name in names)+'\n')
unchanged=[]
for name in re.findall(r'^static [^\n]+\b(samurai_usb_\w+)\(',old,re.M):
    if name not in ['samurai_usb_set_property','samurai_usb_poll','samurai_usb_event']:
        assert function(old,name)==function(source,name),name;unchanged.append(name)
assert (HERE/'samurai-usb-input-decode.h').read_bytes()==(HERE.parent/'usb-input-irq-native-pm-link-candidate/samurai-usb-input-decode.h').read_bytes()
argv=['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I',str(OUT),str(HERE/'test-notify.c'),'-o',str(OUT/'test-notify')]
results=[]
for command in [argv,[str(OUT/'test-notify')]]:
    child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:stdout,stderr=child.communicate()
    finally:child.wait()
    record=dict(argv=command,pid=child.pid,terminal=True,returncode=child.returncode,stdout=stdout.decode(),stderr=stderr.decode())
    results.append(record)
    if child.returncode:break
result=dict(passed=len(results)==2 and all(row['returncode']==0 for row in results),groups=8,
            actual_functions=names,unchanged_original_functions=unchanged,decoder_unchanged=True,
            modeled_OS_boundaries=True,hardware_or_PM_accessed=False,results=results)
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
