"""Only affected offline codec/config branches and fixed OEM reference fragments."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
sys.dont_write_bytecode=True
from fastcharge_codec import *
GENERATED=PRIVATE/'test-output';GENERATED.mkdir(parents=True,exist_ok=True)
def extract_function(text,name):
    m=re.search(r'^(?:static )?(?:bool|int|void) '+name+r'\(',text,re.M)
    if not m:raise ValueError(name)
    start=text.index('{',m.start());depth=1;i=start+1
    while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[m.start():i],text[:m.start()].count('\n')+1
vooc=cached(VOOC).read_text();fw=cached('drivers/power/oppo/vooc_ic/oplus_vooc_fw.c').read_text()
branches,array_block=firmware_branches(cached(HEADER).read_text())
function,func_line=extract_function(fw,'is_allow_fast_chg_real')
# Extract the real top-level dispatch predicates, discarding action bodies.
# This is a differential classifier reference, never the active hardware worker.
start=vooc.index('if (data == VOOC_NOTIFY_FAST_PRESENT)')
clean=uncomment(vooc)
# The adapter-version action has one literal #if 0 / #else pair. Preserve
# offsets while omitting that inactive action's unmatched opening brace.
finish=clean.index('if (chip->fastchg_batt_temp_status',start)
region=clean[start:finish]
assert region.count('#if 0')==1 and region.count('#else')==1
region=re.sub(r'^#if 0\s*\n.*?^#else[^\n]*\n',lambda m:''.join('\n' if x=='\n' else ' ' for x in m[0]),region,flags=re.S|re.M)
clean=clean[:start]+region+clean[finish:]
pos=start;predicates=[]
while True:
    if clean.startswith('if',pos):
        opening=clean.index('(',pos);depth=1;end=opening+1
        while depth:depth+=(clean[end]=='(')-(clean[end]==')');end+=1
        condition=vooc[opening+1:end-1];brace=clean.index('{',end)
    else:condition=None;brace=clean.index('{',pos)
    depth=1;end=brace+1
    while depth:depth+=(clean[end]=='{')-(clean[end]=='}');end+=1
    predicates.append(dict(condition=condition,line=vooc[:pos].count('\n')+1))
    if condition is None:break
    rest=re.match(r'\s*else\s*',clean[end:])
    if not rest:raise ValueError('dispatch chain ended without final else')
    pos=end+rest.end()
assert len(predicates)==15
defines='\n'.join(re.findall(r'^#define\s+VOOC_NOTIFY_[A-Z_]+\s+0x[0-9a-fA-F]+',vooc,re.M))
c='''#include <stdbool.h>
#include <stdio.h>
#include <stddef.h>
#define POWER_SUPPLY_TYPE_USB_DCP 3
#define chg_debug(...) ((void)0)
struct oplus_vooc_chip {int vooc_low_temp,vooc_high_temp,vooc_low_soc,vooc_high_soc;const unsigned char *firmware_data;};
static int temp,cap,chg_type,to_normal;
static int oplus_chg_get_chg_temperature(void){return temp;}
static int oplus_chg_get_ui_soc(void){return cap;}
static int oplus_chg_get_chg_type(void){return chg_type;}
static int oplus_vooc_get_fastchg_to_normal(void){return to_normal;}
'''+defines+'\n'+function+'''
static int classify(int data,int adapter_model_factory,int fw_ver_info,int adapter_fw_ver_info,int present){
 struct oplus_vooc_chip object={.firmware_data=present?(const unsigned char *)"x":NULL};
 struct oplus_vooc_chip *chip=&object;
'''
for i,p in enumerate(predicates):
    c+=(' if' if i==0 else ' else if')+' ('+p['condition']+') return '+str(i)+';\n' if p['condition'] is not None else ' else return '+str(i)+';\n'
c+='}\nint main(void){\n struct oplus_vooc_chip chip={120,430,1,90,NULL};\n'
# USB/CDP/unknown never satisfy the OEM gate; actual DCP gate boundary cases.
gate_cases=[(3,120,1,0,1),(3,429,90,0,1),(3,119,50,0,0),(3,430,50,0,0),
 (3,250,0,0,0),(3,250,91,0,0),(3,250,50,1,0),(1,250,50,0,0),(2,250,50,0,0),(0,250,50,0,0)]
for typ,t,soc,n,expect in gate_cases:
    c+=f' chg_type={typ};temp={t};cap={soc};to_normal={n};if(is_allow_fast_chg_real(&chip)!={expect})return 10;\n'
c+=' for(int ctx=0;ctx<4;ctx++)for(int present=0;present<2;present++)for(int word=0;word<128;word++)\n'
c+=' printf("%d %d %d %d\\n",ctx,present,word,classify(word,ctx==1,ctx==2,ctx==3,present));\n return 0;\n}\n'
(GENERATED/'oem-reference.c').write_text(c)
(HERE/'reference-source.json').write_text(json.dumps(dict(gate_function=dict(name='is_allow_fast_chg_real',line=func_line,sha256=sha(function.encode())),dispatch_predicates=predicates,array_block_sha256=sha(array_block.encode())),indent=2)+'\n')
flags=['-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer']
def compile_run(name,source,extra=()):
    src=GENERATED/(name+'.c');src.write_text(source)
    build=subprocess.run(['gcc',*flags,*extra,str(src),'-o',str(GENERATED/name)],capture_output=True,text=True)
    assert build.returncode==0,build.stderr
    run=subprocess.run([str(GENERATED/name)],capture_output=True)
    assert run.returncode==0,(run.returncode,run.stderr)
    assert not run.stderr
    return run.stdout
raw=compile_run('oem-reference',c).decode()
labels=['FAST_PRESENT','FAST_ABSENT','ADAPTER_MODEL_FACTORY','adapter_model','ALLOW_READING_IIC','NORMAL_TEMP_FULL',
 'LOW_TEMP_FULL','BAD_CONNECTED','TEMP_OVER','BTB_TEMP_OVER','FIRMWARE_UPDATE','mcu_version','adapter_version','ADAPTER_FW_UPDATE','unknown']
contexts=['normal','adapter_model','mcu_version','adapter_version'];diff=0
for line in raw.splitlines():
    ctx,present,word,label=map(int,line.split());bits=f'{word:07b}'
    out=decode_frame(bits,contexts[ctx],bool(present))
    if ctx==0 and not bits.startswith('101'):assert out['kind']=='invalid_prefix'
    else:assert (out['name'] if out['kind']=='notification' else out['kind'])==labels[label],(line,out)
    diff+=1
assert diff==1024
firmware_results={}
for enabled,b in branches.items():
    output=compile_run('array-'+str(enabled).lower(),'#include <stdio.h>\n'+array_block+'\nint main(void){return fwrite('+SYMBOL+',1,sizeof('+SYMBOL+'),stdout)==sizeof('+SYMBOL+')?0:1;}\n',
        ['-DCONFIG_OPLUS_SM8150R_CHARGER'] if enabled else [])
    assert output==b['data']
    firmware_results[str(enabled)]=inspect_stm8s(output,b['data'])
assert firmware_results['True']['firmware_version']==0x18 and firmware_results['False']['firmware_version']==0x3c
bad=[]
image=branches[True]['data']
def rejects(label,fn):
    try:fn()
    except ValueError:bad.append(label);return
    raise AssertionError('accepted '+label)
rejects('truncated record',lambda:inspect_stm8s(image[:-1]))
rejects('empty',lambda:inspect_stm8s(b''))
rejects('oversize',lambda:inspect_stm8s(image*11))
rejects('duplicate address',lambda:inspect_stm8s(image[:34]+image[:34]+image[68:]))
rejects('wrong byte order',lambda:inspect_stm8s(image[1:2]+image[:1]+image[2:]))
rejects('unaligned address',lambda:inspect_stm8s(image[:34]+b'!\x88'+image[36:]))
rejects('wrong config branch',lambda:inspect_stm8s(branches[False]['data'],image))
rejects('one byte differs',lambda:inspect_stm8s(image[:40]+bytes([image[40]^1])+image[41:],image))
rejects('short frame',lambda:decode_frame('101001'))
rejects('long frame',lambda:decode_frame('01010010'))
rejects('nonbinary frame',lambda:decode_frame('1010020'))
rejects('unknown context',lambda:decode_frame('1010010','guess'))
rejects('ambiguous guard',lambda:firmware_branches(cached(HEADER).read_text()*2))
rejects('nonbyte C token',lambda:array_bytes('0x100,'))
rejects('unsupported C token',lambda:array_bytes('0x1,OTHER,'))
subprocess.run(['python3',str(HERE/'extract-config.py')],check=True,stdout=subprocess.DEVNULL)
config=json.loads((HERE/'config-result.json').read_text())
props=config['fastcharge_node']['properties']
assert props['qcom,vooc-fw-type']==[0x22] and props['reg']==[0x26]
assert not config['firmware_update_newmethod_present'] and not config['gpio_ID_properties_present']
assert config['ffc_properties']['qcom,vbatt_num']==[2] and 'qcom,dual_ffc' not in config['ffc_properties']
assert config['divider_node']['properties']['reg']==[0x68,0]
assert firmware_results['True']['gaps']==[dict(after='0x9f80',before='0x9fe0',unrepresented_bytes=64)]
manifest=json.loads((HERE/'source-manifest.json').read_text())
for entry in manifest['files']:assert sha(cached(entry['path']).read_bytes())==entry['sha256']
names=['fastcharge_codec.py','extract-config.py','run-tests.py','reference-source.json','config-result.json','source-manifest.json']
result=dict(passed=True,gate_actual_function_cases=len(gate_cases),dispatch_predicate_differential_cases=diff,
 conditional_array_actual_C_comparisons=2,rejection_boundaries=bad,firmware_images=firmware_results,
 flags=flags,files={n:sha((HERE/n).read_bytes()) for n in names},private_generated={p.name:sha(p.read_bytes()) for p in GENERATED.iterdir() if p.is_file()},
 scope='fixed source metadata and receive classification only; action bodies/hardware timing excluded; source cache is not live MCU firmware',
 phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,hardware_writes=0)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,gate_cases=len(gate_cases),dispatch_cases=diff,actual_arrays=2,rejected=len(bad))))
