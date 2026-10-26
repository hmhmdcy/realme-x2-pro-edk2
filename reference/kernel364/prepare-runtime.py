"""Prepare the corrected-board bootstrap on the verified k363 release."""
from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'source-state.json').read_text())['applied']
assert json.loads((HERE.parent/'kernel363/postboot-validation.json').read_text())['new_boot_verified']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();assert (build/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
state=json.loads((HERE/'source-state.json').read_text());source=build.parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
old=P.parent/'kernel356';facts=json.loads((old/'live-overlay-state-private.json').read_text())
assert facts['firmware_physical']==0x9ab00000 and facts['firmware_bytes']==0x500000 and facts['offline_overlay_named_firmware_resolves']
blob=(old/'boot-test-private.dtbo').read_bytes();header=build/'drivers/media/platform/qcom/camss/camss-icp-a5-boot-test-blob.h'
header.write_text('static const unsigned char a5_boot_test_overlay[] __aligned(8) = {\n'+','.join(str(b) for b in blob)+'\n};\n')
memory_blob=(P.parent/'kernel354/memory-test-private.dtbo').read_bytes()
(header.parent/'camss-icp-a5-memory-test-blob.h').write_text('static const unsigned char a5_memory_test_overlay[] = {\n'+','.join(str(b) for b in memory_blob)+'\n};\n')
(P/'live-overlay-state-private.json').write_text(json.dumps(facts,indent=2)+'\n')
shutil.copyfile(HERE.parent/'kernel356/camss-icp-a5-boot-test.c',HERE/'camss-icp-a5-boot-test.c')
s=(HERE.parent/'kernel356/build-intree.py').read_text().replace('stage=356','stage=364').replace("KBUILD_BUILD_VERSION='298'","KBUILD_BUILD_VERSION='363'")
s=s.replace("modules=['qcom-camss-icp-a5-core','camss-icp-a5-boot-test']", "modules=['qcom-camss-icp-a5-core','camss-icp-a5-boot-test','camss-icp-a5-memory-test']")
s=s.replace("'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST=m'", "'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST=m','CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_MEMORY_TEST=m'")
(HERE/'build-intree.py').write_text(s)
s=(HERE.parent/'kernel356/boot-worker.py').read_text()
# Keep hardware-node/firmware aliases from the verified overlay; only the
# transaction identity and boot guard change. No old transaction is replayed.
(HERE/'boot-worker.py').write_text(s)
s=(HERE.parent/'kernel356/poll-boot.py').read_text().replace('/var/lib/samurai/k356-boot-','/var/lib/samurai/k364-boot-').replace('stage=356','stage=364')
(HERE/'poll-boot.py').write_text(s)
s=(HERE.parent/'kernel356/launch-boot.py').read_text().replace("root='/var/lib/samurai/k356-boot-'","root='/var/lib/samurai/k364-boot-'")
s=s.replace("region=build['firmware_region'];", "build['modules']=[m for m in build['modules'] if m['name'] in ['qcom-camss-icp-a5-core','camss-icp-a5-boot-test']]\nregion=build['firmware_region'];")
s=s.replace("manifest['boot_guard']=json.loads((P/'recovered-boot-adoption-private.json').read_text())['guard_path'] if (P/'recovered-boot-adoption-private.json').exists() else '/var/lib/samurai/k305-geometry-r2/boot-id-private.txt'", "manifest['boot_guard']=json.loads((P.parent/'kernel363/postboot-adoption-private.json').read_text())['guard_path']")
s=s.replace("json.loads((P/'irq-parent-private.json').read_text())", "json.loads((P.parent/'kernel356/irq-parent-private.json').read_text())")
s=s.replace('q=host.raw_ssh(', 'q=host.ssh(')
(HERE/'launch-boot.py').write_text(s)
s=(HERE.parent/'kernel354/memory-worker.py').read_text().replace("Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt')", "Path(json.loads((ROOT/'manifest.json').read_text())['boot_guard'])")
s=s.replace("|[Tt]ranslation fault'", "|[Tt]ranslation fault|OF: ERROR'")
s=s.replace("try:\n assert Path('/proc/sys/kernel/random/boot_id')", "try:\n assert taint_before==0, 'Unexpected taint before IOMMU test'\n assert Path('/proc/sys/kernel/random/boot_id')")
(HERE/'memory-worker.py').write_text(s)
for name in ['build-intree.py','boot-worker.py','poll-boot.py','launch-boot.py']:compile((HERE/name).read_text(),name,'exec')
print('Prepared k363-compatible bootstrap build and fresh k364 transaction; board overlay and OEM ELF reused.')
