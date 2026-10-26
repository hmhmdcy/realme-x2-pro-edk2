from pathlib import Path
import hashlib,json,re

source=Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/sensors-vendor/config/msmnile_mmc5603nj.json')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
payload=source.read_bytes(); text=payload.decode()
try:
    json.loads(text)
    report=dict(strict_json_valid=True)
except json.JSONDecodeError as error:
    # Only syntax punctuation is exposed; manufacturer/default calibration scalars stay private.
    line=text.splitlines()[error.lineno-1]
    masked=re.sub(r'"(?:\\.|[^"\\])*"','"VALUE"',line)
    masked=re.sub(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?','NUMBER',masked)
    report=dict(strict_json_valid=False,error=error.msg,line=error.lineno,column=error.colno,
        masked_error_line=masked)
    without_comments=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    without_comments=re.sub(r'(?m)^\s*//.*$','',without_comments)
    no_trailing_commas=re.sub(r',\s*([}\]])',r'\1',without_comments)
    for name,candidate in (('comments_removed',without_comments),('comments_and_trailing_commas_removed',no_trailing_commas)):
        try:
            obj=json.loads(candidate)
            report[name+'_json_valid']=True
            report[name+'_top_level_keys']=sorted(obj)
        except json.JSONDecodeError:
            report[name+'_json_valid']=False
    try:
        obj=json.loads(text,strict=False)
        controls=[]
        def walk(value,path):
            if isinstance(value,dict):
                for key,item in value.items(): walk(item,path+'/'+key)
            elif isinstance(value,list):
                for i,item in enumerate(value): walk(item,path+'/'+str(i))
            elif isinstance(value,str):
                chars=sorted(set(ord(char) for char in value if ord(char)<32))
                if chars: controls.append(dict(path=path,control_codepoints=chars))
        walk(obj,'')
        report['allowing_literal_control_characters_json_valid']=True
        report['literal_control_character_paths']=controls
    except json.JSONDecodeError:
        report['allowing_literal_control_characters_json_valid']=False
report.update(original_sha256=hashlib.sha256(payload).hexdigest(),phone_configuration_changed=False,
    parser_rejection_on_dsp_proven=False,calibration_values_exposed=False)
(ref/'magnetometer-config-syntax.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
