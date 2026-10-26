from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'observer-regression';work.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
s=(source/'drivers/media/platform/qcom/camss/camss-icp-a5-fw.c').read_text();a=s.index('static u32 ph_word(');b=s.index('int camss_a5_fw_load(',a);(work/'fw-validation.inc').write_text(s[a:b])
s=(P/'camss-icp-a5-boot-test.c.proposed').read_text();a=s.index('static unsigned int snapshot_offsets');b=s.index('static int group_device(',a);(work/'observer.inc').write_text(s[a:b])
(work/'probe.c').write_text((HERE/'observer-regression.c').read_text())
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
rows=[]
for case in range(19):
 q=subprocess.run([str(work/'probe'),str(case),str(P.parent/'kernel352/CAMERA_ICP.elf-private')],capture_output=True,timeout=10);(work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr)
 assert not q.returncode,(case,q.stderr.decode());text=q.stdout.decode()
 data=re.findall(r'data offset=([a-f0-9]+) count=(\d+) values=([^\n]+)',text)
 expected_words=76 if case==0 else 1 if case==16 else 0
 assert sum(int(x[1]) for x in data)==expected_words,(case,text)
 assert ('snapshot end' in text)==(case in [0,16])
 if case==1:assert 'code-match=0' in text
 if case in [2,3,4,5,6]:assert 'unavailable' in text
 rows.append(dict(case=case,printed_words=expected_words,passed=True))
report=dict(stage=372,actual_temporary_observer_configure_bounds_and_dump_bodies=True,actual_common_elf_inspector=True,
 tests=rows,asan_ubsan=True,printk_and_dma_barrier_providers_mocked=True,
 code_mismatch_and_incomplete_ownership_prevent_field_reads=True,range_end_overflow_alignment_counts_and_elf_rejections_checked=True,
 no_allocation_or_mmio_in_fault_observer=True,not_hardware_cache_or_ramoops_proof=True,phone_operations=False,passed=True)
(HERE/'observer-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
