"""Read candidate source and current device before a temporary LTM test."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';state=json.loads((HERE.parent/'kernel405/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
(P/'camss-icp-a5-m2m.c.normal').write_bytes((source/'drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c').read_bytes())
state.update(stage=406,maintained_source_stage=405,source_unchanged_from405=True,temporary_adapter_source_restored=True);(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
build=json.loads((HERE.parent/'kernel405/intree-build-validation.json').read_text());build.update(stage=406,reused_unchanged405_core=True);(HERE/'intree-build-validation.json').write_text(json.dumps(build,indent=2)+'\n')
code=r'''from pathlib import Path
import hashlib,json
d=Path('/sys/bus/platform/devices/ac10000.icp');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
out=dict(same_boot_as394=same_boot,driver=(d/'driver').resolve().name,m2m=json.loads((d/'m2m_status').read_text()),core=json.loads((d/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),test_parameters={n:(Path('/sys/module/camss_icp_a5_m2m/parameters')/n).exists() for n in ['test_cc_mode','test_chain_mode','test_gamma_mode','test_ltm_mode']},normal_core_sha=sha('/lib/modules/'+Path('/proc/sys/kernel/osrelease').read_text().strip()+'/kernel/drivers/media/platform/qcom/camss/qcom-camss-icp-a5-core.ko'),loaded_core_note_sha=sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id'),loaded_adapter_note_sha=sha('/sys/module/camss_icp_a5_m2m/notes/.note.gnu.build-id'))
print(json.dumps(out))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(P/'initial-state-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
assert d['same_boot_as394'] and d['driver']=='qcom-sm8150-icp' and not d['taint'] and not any(d['test_parameters'].values())
assert d['normal_core_sha']=='68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88'
manifest=json.loads((P.parent/'kernel402/manifest-private.json').read_text());assert d['loaded_core_note_sha']==manifest['normal_core_note_sha256'] and d['loaded_adapter_note_sha']==manifest['normal_adapter_note_sha256']
released=not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
print(json.dumps(dict(source_clean=True,maintained_candidate=state['commit'],driver=d['driver'],m2m=d['m2m'],core_released=released,taint=d['taint'],test_parameters=d['test_parameters']),indent=2))
