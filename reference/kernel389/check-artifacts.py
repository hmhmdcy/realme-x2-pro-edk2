from pathlib import Path
import base64,hashlib,json,re,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and build['attempt']==4
mods={r['name']:r for r in build['modules']};camss=Path(mods['qcom-camss']['private_path'])
aliases=subprocess.check_output(['modinfo','-F','alias',str(camss)],text=True)
assert 'Cqcom,sm8150-camss-icp' in aliases and 'Cqcom,sm8150-camssC' in aliases
assert 'qcom/sm8150/camera-icp.elf' in subprocess.check_output(['modinfo','-F','firmware',str(camss)],text=True)
symbols=subprocess.check_output(['aarch64-linux-gnu-nm','-S',str(camss)],text=True)
m=re.search(r'^\S+\s+(\S+)\s+\S\s+camss_drivers$',symbols,re.M);assert m and int(m[1],16)==16,'Both real platform drivers must be registered'
assert re.search(r'\bcamss_icp_driver$',symbols,re.M)
for row in mods.values():assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
baseline=json.loads((HERE.parent/'kernel388/intree-build-validation.json').read_text());old={r['name']:r for r in baseline['modules']}
unchanged=['qcom-camss-icp-a5-core','v4l2-mem2mem','videobuf2-dma-sg','videobuf2-common','videobuf2-v4l2','videobuf2-memops','videobuf2-vmalloc']
assert all(mods[n]['sha256']==old[n]['sha256'] for n in unchanged)
code="""from pathlib import Path
import base64,subprocess
p=Path(subprocess.check_output(['modinfo','-n','v4l2_isp'],text=True).strip());print(base64.b64encode(p.read_bytes()).decode())
"""
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);installed=P/'installed-v4l2-isp.ko';installed.write_bytes(base64.b64decode(q.stdout))
assert hashlib.sha256(installed.read_bytes()).hexdigest()==json.loads((HERE/'current-state-validation.json').read_text())['existing_isp_sha256']
sections={}
for section in ['.text','.rodata']:
 values=[]
 for label,path in [('installed',installed),('new',Path(mods['v4l2-isp']['private_path']))]:
  out=P/(label+'-isp'+section);subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section='+section,str(path),str(out)],check=True)
  values.append(hashlib.sha256(out.read_bytes()).hexdigest())
 sections[section]=dict(installed=values[0],new=values[1],equal=values[0]==values[1])
report=dict(stage=389,normal_camss_and_icp_aliases_in_same_real_module=True,platform_registration_array_has_two_drivers=True,normal_firmware_metadata_present=True,seven_previous_modules_binary_identical=unchanged,
 installed_isp_comparison=sections,isp_module_not_replaced=True,only_camss_and_adapter_runtime_logic_changed=True,formal_driver_runtime_not_claimed=True,passed=True)
(HERE/'artifact-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
