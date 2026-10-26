"""Integrate the A5 core into an isolated real kernel worktree for live work."""
from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
base=storage.mounted_build().parent;source=base/'source354';parent=base/'source348';commit='30086bae4d60abe70784a1176bbe418434833b2f'
if not source.exists():
 q=subprocess.run(['git','-C',str(parent),'worktree','add','-b','samurai-icp-a5-core354',str(source),commit],capture_output=True,timeout=120)
 (P/'worktree-create.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
directory=source/'drivers/media/platform/qcom/camss'
for file in (HERE/'kernel').glob('*'):
 if file.suffix in ['.c','.h']:shutil.copyfile(file,directory/file.name)
make=directory/'Makefile';text=make.read_text()
if 'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_CORE' not in text:
 text+='''
qcom-camss-icp-a5-core-y := camss-icp-a5-core.o camss-icp-a5-hfi.o camss-icp-a5-fw.o camss-icp-a5-memory.o
obj-$(CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_CORE) += qcom-camss-icp-a5-core.o
obj-$(CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_MEMORY_TEST) += camss-icp-a5-memory-test.o
CFLAGS_camss-icp-a5-memory-test.o += -I$(obj)
''';make.write_text(text)
config=directory/'Kconfig';text=config.read_text()
if 'config VIDEO_QCOM_CAMSS_ICP_A5_CORE' not in text:
 text+='''
config VIDEO_QCOM_CAMSS_ICP_A5_CORE
	tristate
	depends on VIDEO_QCOM_CAMSS && IOMMU_DMA

config VIDEO_QCOM_CAMSS_ICP_A5_MEMORY_TEST
	tristate
	depends on VIDEO_QCOM_CAMSS_ICP_A5_CORE && OF_OVERLAY
''';config.write_text(text)
print(json.dumps(dict(source=str(source),parent_commit=commit,integrated_core=True),indent=2))
