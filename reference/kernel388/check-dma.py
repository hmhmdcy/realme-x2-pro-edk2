from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
strip=lambda p:'\n'.join(line for line in p.read_text().splitlines() if not line.startswith('#include'))+'\n'
assert (HERE/'camss-icp-a5-dma.c').read_bytes()==(P/'camss-icp-a5-dma.c.proposed').read_bytes()
code=(HERE/'dma-model-provider.h').read_text()+strip(HERE/'camss-icp-a5-dma.h')+strip(HERE/'camss-icp-a5-dma.c')+(HERE/'dma-model-cases.c').read_text()
model=P/'dma-model.c';model.write_text(code)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(P/'dma-model')],capture_output=True)
(P/'dma-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
q=subprocess.run([str(P/'dma-model')],capture_output=True);(P/'dma-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
match=re.fullmatch(r'DMA_MODEL cases=(\d+) passed=1\n',q.stdout.decode());assert match
report=dict(stage=388,actual_import_sg_range_and_physical_alias_functions=True,asan_ubsan=True,cases=int(match[1]),dmabuf_debug_dma_only_sg_table_modelled=True,importer_does_not_read_sg_pages_or_physical_lengths=True,dma_addresses_not_physical_assumed=True,merged_sg_supported=True,offset_bounds_and_32bit_overflow_checked=True,physical_alias_rejected_through_owned_iommu_domain=True,attachment_and_reference_rollback_balanced=True,domain_change_retains_mapping_and_refs=True,explicit_v4l2_buffer_ownership=True,implicit_async_fence_interop_not_claimed=True,source_sha256=hashlib.sha256((HERE/'camss-icp-a5-dma.c').read_bytes()).hexdigest(),passed=True)
(HERE/'dma-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
