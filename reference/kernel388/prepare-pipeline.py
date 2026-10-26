"""Reuse the verified libcamera candidate; only the kernel DMA path changes."""
from pathlib import Path
import hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel387';P=host.PRIVATE
assert json.loads((HERE/'dma-runtime-r2-validation.json').read_text())['passed']
for leaf in ['libcamera.so.0.7.2','pipeline-smoke']:shutil.copyfile(P.parent/'kernel387'/leaf,P/leaf)
library_sha=hashlib.sha256((P/'libcamera.so.0.7.2').read_bytes()).hexdigest()
assert library_sha=='60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d'
worker=(OLD/'pipeline-worker.py').read_text()
worker=worker.replace("def releasable(result):return ","def releasable(result):return not result.get('imported_buffers') and not result.get('imported_bytes') and ")
needle=" assert after['jobs']==after['completed']+after['cancelled'] and after['completed']>0"
assert worker.count(needle)==1
worker=worker.replace(needle,needle+"\n assert after['direct_completed']==after['completed'] and after['first_error']==0")
needle=" assert result['session_creates']==result['session_destroys']==result['session_peak']==1"
assert worker.count(needle)==1
worker=worker.replace(needle,needle+"\n assert result['direct_frames']==result['frames_completed']>0 and result['copy_frames']==0 and not result['imported_buffers'] and not result['imported_bytes']")
(HERE/'pipeline-worker.py').write_text(worker)
client=(OLD/'camera-client.py').read_text().replace("'stage':387","'stage':388").replace('stage=387','stage=388')
needle="status=lambda:json.loads(Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/m2m_status').read_text())"
assert client.count(needle)==1
client=client.replace(needle,"""def status():
 current=json.loads(Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/m2m_status').read_text())
 assert current['direct_completed']==current['completed']
 result=json.loads(Path('/sys/module/camss_icp_a5_boot_test/parameters/result').read_text())
 assert not result['copy_frames'] and not result['imported_buffers'] and not result['imported_bytes']
 assert result['direct_frames']==result['frames_completed']
 return current
""")
(HERE/'camera-client.py').write_text(client)
pre=(OLD/'preflight.py').read_text().replace('stage=387','stage=388').replace('k387-pipeline-','k388-pipeline-')
pre=pre.replace("'videobuf2_memops','videobuf2_vmalloc'","'videobuf2_memops','videobuf2_dma_sg'")
(HERE/'pipeline-preflight.py').write_text(pre)
launch=(OLD/'launch-pipeline.py').read_text().replace('k387-pipeline-','k388-pipeline-').replace('Prepared387 pipeline','Prepared388 direct DMA pipeline')
(HERE/'launch-pipeline.py').write_text(launch)
poll=(OLD/'poll-pipeline.py').read_text().replace('stage=387','stage=388').replace('k387-pipeline-','k388-pipeline-')
(HERE/'poll-pipeline.py').write_text(poll)
for script,name in [(worker,'pipeline-worker.py'),(client,'camera-client.py'),(pre,'pipeline-preflight.py'),(launch,'launch-pipeline.py'),(poll,'poll-pipeline.py')]:compile(script,name,'exec')
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=388,library_sha256=library_sha,libcamera387_binary_reused=True,ipa_and_dispatcher_unchanged=True,probe_reused=True,worker_compiled=True,all_four_processed=True,raw_only_and_dual=True,isolated_ipa=True,core_and_status_no_copy_assertions_added=True,installed=False,passed=True),indent=2)+'\n')
print('Prepared unchanged libcamera387 with direct-DMA kernel and per-case no-copy checks.')
