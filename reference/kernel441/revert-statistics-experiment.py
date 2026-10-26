from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;storage.mount.mounted_build();tree=storage.candidate()/'src/libcamera-v0.7.2'
q=subprocess.run(['patch','-R','-p1','--batch','--fuzz=0','-i',str(HERE/'0054-camss-ipe-statistics-backlog.patch')],cwd=tree,capture_output=True)
(host.PRIVATE/'statistics-experiment-revert.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'offset' not in q.stdout
p=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha=='e8dd2af61ea1f3f0d0183840c2c0d440abf299699296c371598e44187ab22d79'
state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:
 if row['path']=='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp':row['sha256']=sha
state.update(statistics_pool_tracks_processed_request_backlog=False,statistics_pool_experiment_rejected=True,build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print('Restored the exact post-0053 source; 0054 remains an unaccepted experiment.')
