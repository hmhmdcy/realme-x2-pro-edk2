"""Reuse the bounded DS4 probe with the existing 3M5 2104x1560 mode."""
from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel427';P=host.PRIVATE
assert json.loads((P.parent/'kernel427/intree-build-state.json').read_text())['terminal']
files={}
def write(name,text):
 (HERE/name).write_text(text);files[name]=hashlib.sha256(text.encode()).hexdigest()
text=(OLD/'ds4-capture.c').read_text();assert text.count('"s5kgw1 "')==1
text=text.replace('"s5kgw1 "','"s5k3m5 "');assert len(re.findall(r'\b4608\b',text))==2 and len(re.findall(r'\b3456\b',text))==2
text=re.sub(r'\b4608\b','2104',text);text=re.sub(r'\b3456\b','1560',text);assert 'NV12,640,460800' in text and 'PD10_LOCAL,768,46080' in text;write('ds4-capture.c',text)
text=(OLD/'build-capture.py').read_text().replace('sunny_s5kgw1','qtech_s5k3m5sx').replace("r['tag']=='ds4to1v10_ife_full_dc4'","r['tag']=='ds4to1v10_ife_full_dc4' and r['uid']==33").replace('stage=427','stage=428')
text=text.replace('static_arm64=True','camera_model="s5k3m5",sensor_mode=[2104,1560],same_output_geometry=[640,480,160,120],original_selected_mode_index=0,original_selected_module_uid=33,static_arm64=True');write('build-capture.py',text)
write('capture-worker-body.py',(OLD/'capture-worker-body.py').read_text())
text=(OLD/'prepare-capture.py').read_text().replace("(P/'intree-build-state.json')","(P.parent/'kernel427/intree-build-state.json')").replace("(HERE/'intree-build-validation.json')","(HERE.parent/'kernel427/intree-build-validation.json')").replace("'stage':427","'stage':428").replace('k427-ds4-','k428-ds4-');write('prepare-capture.py',text)
write('capture-runtime.py',(OLD/'capture-runtime.py').read_text().replace('k427-ds4-','k428-ds4-'))
(HERE/'low-input-probe-source-validation.json').write_text(json.dumps(dict(stage=428,source_stage=427,files_sha256=files,
 purpose='Distinguish high sensor input rate from generic DS4 failure using existing telephoto mode',
 camera='s5k3m5',sensor_mode=[2104,1560],output_geometry_unchanged=True,kernel_source_unchanged=True,
 matched_kernel427_build_reused=True,passed=True),indent=2)+'\n')
print('Prepared bounded low-input probe and original mode-selected DS4 calibration.')
