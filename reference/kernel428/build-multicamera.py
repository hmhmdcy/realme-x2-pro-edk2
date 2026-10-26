from pathlib import Path
import hashlib,importlib.util,json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
kernel=m.mounted_build().parent/'source354';inc=P/'capture-includes';(inc/'linux/media').mkdir(parents=True,exist_ok=True)
for name in ['qcom-camss-config.h','media/v4l2-isp.h','media-bus-format.h']:shutil.copyfile(kernel/'include/uapi/linux'/name,inc/'linux'/name)
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I'+str(inc),str(HERE/'ds4-capture.c'),'-o',str(P/'ds4-capture')],capture_output=True)
(P/'multicamera-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
rows=[]
for model,variant,mode in [('s5kgw1','sunny_s5kgw1',2),('s5k3m5','qtech_s5k3m5sx',0),('imx471','sunny_imx471',1),('imx319','sunny_imx319',0)]:
 selections=json.loads((P.parent/'kernel426'/(variant+'-ds4-selection-private.json')).read_text())
 selected=next(r for r in selections if r['sensor_mode_index']==mode and r['usecase']=='Preview' and r['tag']=='ds4to1v10_ife_full_dc4')
 root=next(r for r in json.loads((P.parent/'kernel426'/(variant+'-ds4-reserves-private.json')).read_text()) if r['tag']==selected['tag'] and r['uid']==selected['uid'])
 coefs=root['passes'][0][1:];assert len(coefs)==3 and all(0<=x<=256 for x in coefs)
 wb=struct.pack('<HHI12H',1,2,32,1024,1024,1024,*([0]*9));ds4=struct.pack('<HHI4H',8,0,16,*coefs,0)
 (P/('params-'+model+'-private.bin')).write_bytes(struct.pack('<2I',1,len(wb)+len(ds4))+wb+ds4)
 rows.append(dict(model=model,variant=variant,sensor_mode_index=mode,module_uid=selected['uid'],tag=selected['tag']))
report=dict(stage=428,static_arm64=True,compiler_warnings=[],source_sha256=hashlib.sha256((HERE/'ds4-capture.c').read_bytes()).hexdigest(),probe_sha256=hashlib.sha256((P/'ds4-capture').read_bytes()).hexdigest(),calibration_bindings=rows,private_oem_payload_bytes_per_camera=56,passed=True)
(HERE/'capture-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'multicamera-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
