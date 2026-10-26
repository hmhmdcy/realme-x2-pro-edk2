"""Keep temporary diagnostic modules pinned while any power resources remain."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'collector-validation.json').read_text())['passed']
assert json.loads((HERE.parent/'kernel368/intree-build-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';parent=json.loads((HERE.parent/'kernel368/source-state.json').read_text())['commit']
git=lambda *args:subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot-test.c';before=(source/relative).read_text();s=before
old='!device_a5->cpu_enabled && !device_a5->power_held) {'
assert s.count(old)==1;s=s.replace(old,'!device_a5->cpu_enabled && !device_a5->power_held &&\n\t    !device_a5->resources.enabled_groups && !device_a5->resources.held_domains) {')
old='(camss_a5_backing_owned(a5) || a5->cpu_enabled || a5->power_held) && !pinned'
assert s.count(old)==1;s=s.replace(old,'(camss_a5_backing_owned(a5) || a5->cpu_enabled || a5->power_held ||\n\t     a5->resources.enabled_groups || a5->resources.held_domains) && !pinned')
(HERE/'camss-icp-a5-boot-test.c').write_text(s)
(HERE/'diagnostic-ownership.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-sfr-diagnostic369'],check=True,capture_output=True)
(source/relative).write_text(s);subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',relative],check=True);subprocess.run(['git','-C',str(source),'commit','-m','media: camss: retain A5 diagnostic owner while power resources remain'],check=True,capture_output=True)
facts=json.loads((P.parent/'kernel366/live-overlay-state-private.json').read_text());(P/'live-overlay-state-private.json').write_text(json.dumps(facts,indent=2)+'\n')
# Reuse the exact static-board overlay already verified and exercised in366.
blob=(P.parent/'kernel366/boot-test-private.dtbo').read_bytes()
(build/'drivers/media/platform/qcom/camss/camss-icp-a5-boot-test-blob.h').write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
s=(HERE.parent/'kernel366/build-intree.py').read_text().replace('stage=366','stage=369')
s=s.replace("modules=['qcom-camss-icp-a5-core','camss-icp-a5-boot-test','camss-icp-a5-memory-test']","modules=['qcom-camss-icp-a5-core','camss-icp-a5-boot-test']")
s=s.replace(",'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_MEMORY_TEST=m'",'')
(HERE/'build-intree.py').write_text(s)
report=dict(stage=369,source=str(source),parent=parent,commit=git('rev-parse','HEAD'),branch='samurai-a5-sfr-diagnostic369',changed=[relative],
    core_semantics_source_stage=368,static_dt_overlay_identical_to366=True,installed=False,firmware_cpu_started=False)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
