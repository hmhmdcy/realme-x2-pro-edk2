"""Add narrow lifecycle observations to distinguish DMA retirement and PM release."""
from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent=json.loads((HERE.parent/'kernel370/source-state.json').read_text())['commit'];assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c';before=(source/relative).read_text();s=before
anchor='\tret = free_memory(a5);\n\tif (ret)\n\t\treturn ret;\n\tif (a5->power_held) {'
new='''\tdev_info(a5->dev, "A5 retiring DMA aliases\\n");
\tret = free_memory(a5);
\tif (ret)
\t\treturn ret;
\tdev_info(a5->dev, "A5 DMA aliases retired\\n");
\tif (a5->power_held) {'''
assert s.count(anchor)==1;s=s.replace(anchor,new)
anchor='\t\ta5->power_held = false;\n\t\tif (ret < 0)'
assert s.count(anchor)==1;s=s.replace(anchor,'\t\ta5->power_held = false;\n\t\tdev_info(a5->dev, "A5 PM reference released: %d\\n", ret);\n\t\tif (ret < 0)')
(HERE/'a5-teardown-observations.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
subprocess.run(['git','-C',str(source),'switch','-c','samurai-a5-held-snapshot371'],capture_output=True,check=True)
(source/relative).write_text(s);subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',relative],check=True);subprocess.run(['git','-C',str(source),'commit','-m','media: camss: identify A5 DMA and PM teardown boundaries'],capture_output=True,check=True)
(P/'camss-icp-a5-boot.c.proposed').write_text(s);(P/'camss-icp-a5-boot.c.before').write_text(before)
for name in ['camss-icp-a5-boot.h','camss-icp-a5-boot-test.c']:
 (P/(name+'.proposed')).write_bytes((source/Path(relative).parent/name).read_bytes())
(HERE/'camss-icp-a5-boot-test.c').write_bytes((P/'camss-icp-a5-boot-test.c.proposed').read_bytes())
(P/'live-overlay-state-private.json').write_bytes((P.parent/'kernel370/live-overlay-state-private.json').read_bytes())
blob=(P.parent/'kernel366/boot-test-private.dtbo').read_bytes();(build/'drivers/media/platform/qcom/camss/camss-icp-a5-boot-test-blob.h').write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
(HERE/'build-intree.py').write_text((HERE.parent/'kernel370/build-intree.py').read_text().replace('stage=370','stage=371'))
report=dict(stage=371,commit=git('rev-parse','HEAD'),branch='samurai-a5-held-snapshot371',parent=parent,source=str(source),
 changed=[relative],lifecycle_semantics_source_stage=370,installed=False,firmware_cpu_started=False)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
