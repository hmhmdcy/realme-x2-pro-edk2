from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
text=(HERE/'samurai-usb-input.c').read_text()
base=(HERE/'baseline-samurai-usb-input.c').read_text()
sha=lambda b:hashlib.sha256(b).hexdigest()
def function(source,name):
 m=re.search(r'^static (?:enum power_supply_usb_type |unsigned long long |ssize_t |int |void )(?:__(?:init|exit) )?'+name+r'\([^;]*?\)\s*\{',source,re.M)
 assert m,name
 start=m.start();pos=source.index('{',start);depth=0
 for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',source[pos:],re.S):
  if token.group()=='{':depth+=1
  if token.group()=='}':
   depth-=1
   if depth==0:return source[start:pos+token.end()]
 raise AssertionError(name)
names=['samurai_usb_read_status','samurai_usbin_now','samurai_usbin_config','samurai_usbin_snapshot',
 'samurai_usbin_clear_bit','samurai_usbin_prepare','samurai_usbin_step_locked','usbin_init_state_show',
 'samurai_usb_get_budget','samurai_usb_type','samurai_usb_get_property','samurai_usb_set_property',
 'samurai_usb_poll','samurai_usb_stop','samurai_usb_suspend','samurai_usb_resume','samurai_usb_retain_for_native_consumer']
functions=[function(text,n) for n in names]
(HERE/'tested-functions.inc').write_text('\n\n'.join(functions)+'\n')
struct=re.search(r'^enum samurai_usbin_stage \{.*?^\};.*?^struct samurai_usb_input \{.*?^\};',text,re.M|re.S).group()
(HERE/'tested-struct.inc').write_text(struct+'\n')
unchanged=['samurai_usb_read_status','samurai_usb_get_budget','samurai_usb_type','samurai_usb_get_property','samurai_usb_set_property','samurai_usb_resume','samurai_usb_parent_match','samurai_usb_init','samurai_usb_exit']
for n in unchanged:assert function(base,n)==function(text,n),n
retain=function(base,'samurai_usb_retain_for_native_consumer').replace('\t\t__module_get(THIS_MODULE);','\t\t__module_get(THIS_MODULE);\n\t\tnative_ref_held = true;')
assert retain==function(text,'samurai_usb_retain_for_native_consumer')
probe=function(text,'samurai_usb_probe')
assert probe.index('samurai_usb_retain_for_native_consumer(dev)')<probe.index('samurai_usbin_prepare(input)')<probe.index('schedule_delayed_work')
assert '\tmutex_lock(&input->lock);\n\tsamurai_usbin_prepare(input);\n\tmutex_unlock(&input->lock);' in probe
assert 'msecs_to_jiffies(1000)' in function(text,'samurai_usb_poll')
assert text.count('regmap_update_bits(')==1
assert (HERE/'usbin-init-core.h').read_bytes()==(HERE.parent/'apsd-usbin-init-candidate/usbin-init-core.h').read_bytes()
assert (HERE/'samurai-usb-input-decode.h').read_bytes()==(HERE.parent/'source-float-candidate/samurai-usb-input-decode.h').read_bytes()
# Registration and source budget description also unchanged.
for name in ['samurai_usb_desc','samurai_usb_properties']:
 pattern=r'^static [^;{]*\b'+name+r'(?:\[\])? = \{.*?^\};'
 assert re.search(pattern,base,re.M|re.S).group()==re.search(pattern,text,re.M|re.S).group(),name
manifest=dict(actual_functions=[dict(name=n,line=text[:text.index(f)].count('\n')+1,sha256=sha(f.encode())) for n,f in zip(names,functions)],
 unchanged_production_functions=unchanged,unchanged_core_sha256=sha((HERE/'usbin-init-core.h').read_bytes()),
 unchanged_decoder_sha256=sha((HERE/'samurai-usb-input-decode.h').read_bytes()),poll_ms=1000)
(HERE/'function-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
