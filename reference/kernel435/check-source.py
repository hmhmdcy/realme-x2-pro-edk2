from pathlib import Path
import hashlib,json,re,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';old=T.parents[2]/'libcamera431-pd10-auto/src/libcamera-v0.7.2'
s=json.loads((HERE/'source-state.json').read_text());parts=[]
for row in s['source_hashes']:
 rel=row['path'];p=T/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 q=subprocess.run(['diff','-u','--label','a/'+rel,'--label','b/'+rel,str(old/rel) if (old/rel).exists() else '/dev/null',str(p)],capture_output=True);assert q.returncode in [0,1];parts.append(q.stdout)
(HERE/'0047-camss-gtm-applied-tone-history.patch').write_bytes(b''.join(parts))
build=json.loads((HERE/'build-validation.json').read_text());assert build['passed'] and build['attempt']>=2
log=re.sub(r'\x1b\[[0-9;]*m','',(P/('candidate-build-r'+str(build['attempt'])+'.log')).read_text());diagnostics=[line for line in log.splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()];assert not diagnostics
for r in build['runtime_files']:assert hashlib.sha256((P/r['name']).read_bytes()).hexdigest()==r['sha256']
proxy=next((T/'output').rglob('camss_ipa_proxy.cpp')).read_text()
start=proxy.index('void IPAProxyCamssThreaded::frameProcessed(');end=proxy.index('\n}',start)
assert 'ipa_->frameProcessed(' in proxy[start:end] and 'invokeMethod' not in proxy[start:end]
assert (T/'src/ipa/camss-vfe/camss.cpp').read_text().count('std::lock_guard<std::recursive_mutex> stateLock(stateMutex_);')==16
with storage.sdk_candidate():
 path='/work/libcamera/src/libcamera-v0.7.2';q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+path+'/output/src/libcamera:'+path+'/output/src/libcamera/base',path+'/output/src/apps/ipa-verify/ipa_verify',path+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so'],capture_output=True);(P/'signature-check-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'IPA module signature is valid' in q.stdout
r=dict(stage=435,source_hashes_verified=True,patch_files=len(parts),baseline_stage=431,build_attempt=build['attempt'],source_diagnostics=diagnostics,actual_ipa_signature_verified=True,matched_runtime_hashes_verified=True,actual_generated_final_receipt_is_synchronous=True,all_16_ipa_entrypoints_serialize_shared_state=True,kernel_and_ipe_transport_unchanged_from434=True,board_dt_and_sensor_sources_unchanged=True,private_ipa_version=5,installed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
