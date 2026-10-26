from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
candidate=(HERE/'bq27xxx_battery.c').read_text();baseline=(HERE/'baseline-bq27xxx_battery.c').read_text()
def function(s,name):
 m=re.search(r'^(?:static )?(?:inline )?(?:int|void|bool)\s+'+name+r'\([^;]*?\)\s*\{',s,re.M);assert m,name
 start=m.start();pos=s.index('{',start);depth=0
 for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',s[pos:],re.S):
  if token.group()=='{':depth+=1
  if token.group()=='}':
   depth-=1
   if not depth:return s[start:pos+token.end()]
 raise AssertionError(name)
names=['bq27xxx_read','bq27xxx_samurai_instant','bq27xxx_samurai_props','bq27xxx_samurai_average_current',
 'bq27xxx_battery_is_full','bq27xxx_battery_current_and_status','bq27xxx_battery_update_unlocked',
 'bq27xxx_battery_update','bq27xxx_battery_get_property']
functions=[function(candidate,n) for n in names]
for n in ['bq27xxx_read','bq27xxx_battery_is_full','bq27xxx_battery_update_unlocked','bq27xxx_battery_update','bq27xxx_external_power_changed']:
 assert function(candidate,n)==function(baseline,n),n
orig=function(baseline,'bq27xxx_battery_current_and_status').replace('bq27xxx_battery_current_and_status','original_current_and_status',1)
(HERE/'tested-functions.inc').write_text('\n\n'.join(functions)+'\n\n'+orig+'\n')
arrays=[]
for name in ['bq28z610_props','bq28z610_samurai_props']:
 arrays.append(re.search(r'^static enum power_supply_property '+name+r'\[\] = \{.*?^\};',candidate,re.M|re.S).group())
assert arrays[0]==re.search(r'^static enum power_supply_property bq28z610_props\[\] = \{.*?^\};',baseline,re.M|re.S).group()
assert arrays[1].replace('bq28z610_samurai_props','bq28z610_props').replace('\n\tPOWER_SUPPLY_PROP_CURRENT_AVG,','')==arrays[0]
reg_enum=re.search(r'^enum bq27xxx_reg_index \{.*?^\};',candidate,re.M|re.S).group()
(HERE/'tested-declarations.inc').write_text(reg_enum+'\n'+'\n'.join(arrays)+'\n')
assert 'power_supply_is_supplied' not in candidate
assert function(candidate,'bq27xxx_battery_setup').count('bq27xxx_samurai_props(di, psy_desc);')==1
manifest=dict(actual_functions=[dict(name=n,sha256=hashlib.sha256(f.encode()).hexdigest(),line=candidate[:candidate.index(f)].count('\n')+1) for n,f in zip(names,functions)],
 oracle='original unmodified current/status actual function',unchanged_default_array=True,unchanged_update_and_notification_functions=True)
(HERE/'function-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
