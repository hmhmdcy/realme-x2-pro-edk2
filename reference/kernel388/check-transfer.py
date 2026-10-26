from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
strip=lambda p:'\n'.join(line for line in p.read_text().splitlines() if not line.startswith('#include'))+'\n'
s=(P/'camss-icp-a5-boot.c.proposed').read_text()
def function(name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert m,name;return m.group()
dma=(HERE/'dma-model-provider.h').read_text()+strip(HERE/'camss-icp-a5-dma.h')+strip(HERE/'camss-icp-a5-dma.c')
provider=(HERE/'transfer-model-provider.h').read_text()
# Declarations from the actual public internal job/encoder header, followed
# by deterministic firmware providers. Encoder/HFI packet proofs are reused.
ipe=strip(P/'camss-icp-a5-ipe.h.proposed')
tests=(HERE/'transfer-model-cases.c').read_text();split=tests.index('int main(void)')
encoder=tests[:split].replace('static int camss_a5_ipe_','int camss_a5_ipe_')
code=dma+provider+ipe+encoder+'\n'.join(function(n) for n in ['nv12_layout_valid','camss_a5_backing_owned','free_imported_images','free_memory','free_transfer_memory','transfer_region_locked','transfer_alloc','camss_a5_ipe_run'])+tests[split:]
model=P/'transfer-model.c';model.write_text(code)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(P/'transfer-model')],capture_output=True)
(P/'transfer-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
q=subprocess.run([str(P/'transfer-model')],capture_output=True);(P/'transfer-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
match=re.fullmatch(r'TRANSFER_MODEL cases=(\d+) passed=1\n',q.stdout.decode());assert match
report=dict(stage=388,actual_core_transfer_and_free_functions=True,actual_dma_import_and_alias_functions=True,asan_ubsan=True,cases=int(match[1]),native_mode_no_input_or_output_bounce_allocations=True,legacy_pointer_fixture_kept=True,mixed_modes_rejected=True,uncertain_map_frame_and_unmap_keep_imported_refs=True,queue_refs_dropped_while_core_pin_retained=True,failed_quiesce_cannot_free_images=True,successful_quiesce_releases_imports_and_request=True,firmware_mmio_and_encoder_provider_only=True,no_hardware_or_full_error_concurrency_claim=True,passed=True)
(HERE/'transfer-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
