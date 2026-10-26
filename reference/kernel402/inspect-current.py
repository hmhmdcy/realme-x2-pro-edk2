"""Read the actual source and relevant live state before the next transition."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='b8ce3ce92745a11b039e1335e87bbb2dd783c2c7'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
base=source/'drivers/media/platform/qcom/camss'
(P/'camss-icp-a5-m2m.c.before').write_bytes((base/'camss-icp-a5-m2m.c').read_bytes())
code=r'''from pathlib import Path
import hashlib,json
d=Path('/sys/bus/platform/devices/ac10000.icp')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
out=dict(driver=(d/'driver').resolve().name,m2m=json.loads((d/'m2m_status').read_text()),core=json.loads((d/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),test_parameters={n:(Path('/sys/module/camss_icp_a5_m2m/parameters')/n).exists() for n in ['test_cc_mode','test_chain_mode','test_gamma_mode']},normal_core_sha=hashlib.sha256(Path('/lib/modules/'+Path('/proc/sys/kernel/osrelease').read_text().strip()+'/kernel/drivers/media/platform/qcom/camss/qcom-camss-icp-a5-core.ko').read_bytes()).hexdigest())
print(json.dumps(out))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(P/'initial-state-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
assert d['driver']=='qcom-sm8150-icp' and not d['taint'] and not any(d['test_parameters'].values())
assert d['normal_core_sha']=='68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88'
print(json.dumps(dict(source_clean=True,driver=d['driver'],m2m=d['m2m'],core_released=not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes']),taint=d['taint'],test_parameters=d['test_parameters']),indent=2))
