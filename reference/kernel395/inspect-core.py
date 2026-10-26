from pathlib import Path
import importlib.util,re
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';s=(source/'drivers/media/platform/qcom/camss/camss-icp-a5-boot.c').read_text()
for name in ['capture_shared_state','free_imported_images','free_memory','quiesce_locked','camss_a5_start','camss_a5_runtime_suspend']:
 m=re.search(r'(?:static )?(?:void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',s,re.S|re.M)
 if m:print(m.group())
print((source/'drivers/clk/qcom/reset.c').read_text())
