"""First exercise direct DMA with the existing pixel-comparing V4L2 client."""
from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel386';P=host.PRIVATE
for leaf in ['dma','transfer','intree-build']:assert json.loads((HERE/(leaf+'-validation.json')).read_text())['passed']
worker=(OLD/'m2m-worker.py').read_text()
worker=worker.replace("str(ROOT/'snapshot-collector.py'),str(ROOT)]","str(ROOT/'snapshot-collector.py'),str(ROOT),'--seconds','120']")
anchor=" assert after['jobs']==after['completed']==18 and after['starts']==3"
assert worker.count(anchor)==1
worker=worker.replace(anchor,anchor+"\n assert after['direct_completed']==18 and after['cancelled']==0")
anchor=" assert result['frames_completed']==result['image_frames']==8"
assert worker.count(anchor)==1
worker=worker.replace(anchor,anchor+"\n assert result['direct_frames']==8 and result['copy_frames']==0 and result['imported_buffers']==result['imported_bytes']==0")
worker=worker.replace(" (ROOT/'collector-stop').touch()\n deadline=time.monotonic()+13"," assert collector.poll() is None,'Collector must cover the complete native client'\n (ROOT/'collector-stop').touch()\n deadline=time.monotonic()+13")
worker=worker.replace("def releasable(result):return ","def releasable(result):return not result.get('imported_buffers') and not result.get('imported_bytes') and ")
compile(worker,'m2m-worker.py','exec');(HERE/'m2m-worker.py').write_text(worker)
shutil.copyfile(OLD/'snapshot-collector.py',HERE/'snapshot-collector.py')
pre=(HERE.parent/'kernel387/preflight.py').read_text().replace("HERE/'pipeline-worker.py'","HERE/'m2m-worker.py'").replace('stage=387','stage=388').replace('k387-pipeline-','k388-dma-')
pre=pre.replace("'videobuf2_memops','videobuf2_vmalloc'","'videobuf2_memops','videobuf2_dma_sg'")
(HERE/'preflight.py').write_text(pre)
launch=(OLD/'launch-m2m.py').read_text()
launch=launch.replace("for name in ['m2m','worker','client-build','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']","for name in ['dma','transfer','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']")
launch=launch.replace("(HERE/'client-build-validation.json')","(HERE.parent/'kernel386/client-build-validation.json')").replace("(HERE/'firmware-context-validation.json')","(HERE.parent/'kernel386/firmware-context-validation.json')")
launch=launch.replace('k386-m2m-','k388-dma-').replace('Prepared386 held-failure','Prepared388 native DMA')
(HERE/'launch-dma.py').write_text(launch)
poll=(OLD/'poll-m2m.py').read_text().replace('stage=386','stage=388').replace('k386-m2m-','k388-dma-').replace('m2m-runtime-','dma-runtime-').replace('m2m-runtime-validation','dma-runtime-validation')
(HERE/'poll-dma.py').write_text(poll)
for text,name in [(pre,'preflight.py'),(launch,'launch-dma.py'),(poll,'poll-dma.py')]:compile(text,name,'exec')
(HERE/'runtime-preparation-validation.json').write_text(json.dumps(dict(stage=388,unchanged_pixel_comparing_client_reused_stage=386,source_offset_and_padded_stride_and_two_contexts=True,mmapped_and_imported_buffers_both_direct=True,no_copy_counters_required=True,collector_window_seconds=120,worker_compiled=True,passed=True),indent=2)+'\n')
print('Prepared direct DMA transaction and unchanged pixel-comparing native client.')
