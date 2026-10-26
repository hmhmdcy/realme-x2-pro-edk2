from pathlib import Path
import ast,hashlib,importlib.util,json,shlex,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics']
rows={r['name']:r for r in build['modules']};original={r['name']:r for r in json.loads((HERE.parent/'kernel389/intree-build-validation.json').read_text())['modules']}
prior=json.loads((P.parent/'kernel389/module-stage-manifest-private.json').read_text());targets={r['name']:r for r in prior['modules']}
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':393")
prefix=prefix.replace("marker.write_text(json.dumps(state,indent=2)+'\\n')", "tmp=root/'state.tmp';tmp.write_text(json.dumps(state,indent=2)+'\\n');tmp.replace(marker)")
worker=prefix+'\n'+(HERE/'deploy-worker-body.py').read_text();ast.parse(worker);(P/'worker.py').write_text(worker)
collector=(HERE.parent/'kernel391/dump-collector.py').read_text().replace('start<600','start<180').replace('start>=600','start>=180');(P/'dump-collector.py').write_text(collector)
files={'worker.py':P/'worker.py','dump-collector.py':P/'dump-collector.py','local-error-client':P/'local-error-client'};modules=[]
for name in ['qcom-camss-icp-a5-core','camss-icp-a5-m2m']:
 row=rows[name];assert row['runtime_candidate'];file=name+'.ko';files[file]=Path(row['private_path']);r=dict(module=name.replace('-','_'),file=file,target='/lib/modules/'+prior['release']+'/'+targets[name]['target_relative'],old_sha256=original[name]['sha256'],new_sha256=row['sha256'])
 for kind,record in [('old',original[name]),('new',row)]:
  note=P/(name+'-'+kind+'.note');subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.note.gnu.build-id',record['private_path'],str(note)],check=True);r[kind+'_note_sha256']=hashlib.sha256(note.read_bytes()).hexdigest()
 modules.append(r)
new_symbols=subprocess.check_output(['aarch64-linux-gnu-nm','--defined-only',rows['qcom-camss-icp-a5-core']['private_path']],text=True)
assert '__ksymtab_camss_a5_ipe_run_status' in new_symbols and '__ksymtab_camss_a5_ipe_run\n' in new_symbols
assert rows['videobuf2-dma-sg']['sha256']==original['videobuf2-dma-sg']['sha256'] and rows['v4l2-mem2mem']['sha256']==original['v4l2-mem2mem']['sha256']
proof=json.loads((P.parent/'kernel391/install-proof-private.json').read_text())
meta=dict(stage=393,release=prior['release'],modules=modules,payload_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},camss_note_sha256=proof['camss_note_sha256'],profiles=proof['private_defaults'])
(P/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');files['manifest.json']=P/'manifest-private.json'
payload=P/'runtime-payload-private.tar.gz';assert not payload.exists()
with tarfile.open(payload,'w:gz') as t:
 for n,p in files.items():t.add(p,arcname=n,recursive=False)
root='/var/lib/samurai/k393-deployment-r1';code=r'''from pathlib import Path
import hashlib,json
root=Path(ROOT);assert not root.exists();meta=META
for r in meta['modules']:
 assert hashlib.sha256(Path(r['target']).read_bytes()).hexdigest()==r['old_sha256']
 assert hashlib.sha256(Path('/sys/module',r['module'],'notes/.note.gnu.build-id').read_bytes()).hexdigest()==r['old_note_sha256']
dev=Path('/sys/bus/platform/devices/ac10000.icp');s=json.loads((dev/'m2m_status').read_text());assert not any(s[k] for k in ['users','running','fatal','pinned','orphans'])
root.mkdir(mode=0o700);print(json.dumps(dict(stage=393,initial_m2m=s,staging_created=True)))
'''.replace('ROOT',repr(root)).replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(P/'preflight-private.json').write_bytes(q.stdout)
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(payload,root+'/payload-private.tar.gz');(P/'upload-private.log').write_bytes(q.stdout+q.stderr)
fixture_sha=hashlib.sha256((P.parent/'kernel363/pipeline-fixture').read_bytes()).hexdigest()
code=r'''from pathlib import Path
import hashlib,json,shutil,tarfile
root=Path(ROOT);assert hashlib.sha256((root/'payload-private.tar.gz').read_bytes()).hexdigest()==SHA
with tarfile.open(root/'payload-private.tar.gz','r:gz') as t:
 members=t.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
 for m in members:
  with (root/m.name).open('xb') as f:f.write(t.extractfile(m).read())
shutil.copyfile('/var/lib/samurai/k391-install-r2/pipeline-fixture',root/'pipeline-fixture');assert hashlib.sha256((root/'pipeline-fixture').read_bytes()).hexdigest()==FIXTURE_SHA
for n in ['local-error-client','pipeline-fixture']:(root/n).chmod(0o700)
meta=json.loads((root/'manifest.json').read_text());meta['payload_sha256']['pipeline-fixture']=FIXTURE_SHA;(root/'manifest.json').write_text(json.dumps(meta)+'\n')
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
print(json.dumps(dict(stage=393,staged=True,only_two_modules_to_replace=True,old_api_symbol_kept=True,standard_sg_and_m2m_helpers_identical=True,installed=False,passed=True)))
'''.replace('ROOT',repr(root)).replace('SHA',repr(hashlib.sha256(payload.read_bytes()).hexdigest()),1).replace('NAMES',repr(set(files))).replace('FIXTURE_SHA',repr(fixture_sha))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(HERE/'staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
