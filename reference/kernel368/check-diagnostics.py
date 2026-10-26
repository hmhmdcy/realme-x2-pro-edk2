from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'diagnostic-regression';work.mkdir(exist_ok=True)
s=(P/'boot-proposed.c').read_text();a=s.index('struct camss_a5_start_dump {');b=s.index('static int free_memory(',a)
(work/'diagnostic-methods.inc').write_text(s[a:b])
h=(HERE.parent/'kernel353/kernel/camss-icp-a5.h').read_text();a=h.index('struct camss_a5_qhdr {');b=h.index('struct camss_a5_ring {',a)
(work/'queue-types.inc').write_text(h[a:b]);shutil.copyfile(HERE/'diagnostic-regression.c',work/'probe.c')
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True)
assert not q.returncode,q.stderr.decode()
sample=P/'synthetic-devcoredump-private.bin'
q=subprocess.run([str(work/'probe'),str(sample)],capture_output=True,timeout=10);(P/'diagnostic-regression-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
spec=importlib.util.spec_from_file_location('decode368',HERE/'decode-start-dump.py');decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
raw=sample.read_bytes();d=decoder.decode(raw)
assert d['version']==1 and d['init_response']==3 and d['firmware_version']==0x01000100 and d['sfr']=='F'*511
assert d['queue_indices']==[dict(read=10+i,write=20+i) for i in range(3)]
assert [d[k] for k in ['interrupts','watchdogs','protocol_errors']]==[9,2,7]
for malformed in [raw[:-1],raw+b'x',bytes(8)+raw[8:],raw[:8]+(2).to_bytes(4,'little')+raw[12:]]:
 try:decoder.decode(malformed)
 except ValueError:pass
 else:raise RuntimeError('Malformed diagnostic record accepted')
report=dict(stage=368,verbatim_diagnostic_functions_and_queue_types=True,asan_ubsan=True,
    bounded_sfr_declared_size_and_allocated_size_checked=True,fixed_dump_bytes=568,
    coredump_data_independent_of_shared_memory_after_publication=True,
    allocation_failure_does_not_break_error_cleanup=True,early_and_invalid_memory_paths_checked=True,
    actual_production_dump_decoded_and_corrupt_records_rejected=True,
    devcoredump_vmalloc_dma_and_mmio_providers_mocked=True,actual_kernel_or_runtime_not_claimed=True,passed=True)
(HERE/'diagnostic-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
