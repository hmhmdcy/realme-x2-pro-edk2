from pathlib import Path
import difflib,hashlib,importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;state=json.loads((HERE/'source-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
source=mount.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
for leaf in state['changed']:
 assert (source/'drivers/media/platform/qcom/camss'/leaf).read_bytes()==(P/(leaf+'.proposed')).read_bytes(),leaf
for relative in state['framework_changed']:assert (source/relative).read_bytes()==(P/(Path(relative).name+'.proposed')).read_bytes()
patch=''
for relative in ['drivers/media/platform/qcom/camss/'+n for n in state['changed']]+state['framework_changed']:
 q=subprocess.run(['git','-C',str(source),'show',state['parent']+':'+relative],capture_output=True,text=True)
 assert q.returncode==0 or relative.endswith(('camss-icp-a5-dma.c','camss-icp-a5-dma.h'))
 a=q.stdout if q.returncode==0 else '';b=(source/relative).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+relative if a else '/dev/null',tofile='b/'+relative))
assert patch==(HERE/'direct-dma.patch').read_text()
assert hashlib.sha256((P/'libcamera.so.0.7.2').read_bytes()).hexdigest()=='60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d'
# Reuse the preceding precise idle/rails/node inventory; replace only stage workers.
previous=(HERE.parent/'kernel387/close-current.py').read_text();code=previous.split('code="""',1)[1].split('"""',1)[0]
code=code.replace("root in Path('/var/lib/samurai').glob('k387-pipeline-r*')", "root in list(Path('/var/lib/samurai').glob('k388-dma-r*'))+list(Path('/var/lib/samurai').glob('k388-pipeline-r*'))+[Path('/var/lib/samurai/k388-framework-r1'),Path('/var/lib/samurai/k388-framework-r1/native'),Path('/var/lib/samurai/k388-framework-r1/pipeline')] if (root/'state.json').exists()")
code=code.replace("'camera-client.py'))","'camera-client.py') or live(root,'client_pid','m2m-client') or live(root,'export_client_pid','export-lifetime-client'))")
# Original source string was embedded, decode the one escaped NUL literal used there.
code=code.replace("b'\\\\0'","b'\\0'")
baseline=json.loads((P/'sg-runtime-baseline-private.json').read_text())
code+="\nimport hashlib\nfor n,row in "+repr(baseline)+".items():\n assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['file_sha256']\n assert hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest()==row['note_sha256']\n"
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=25).stdout)
assert not d['taint'] and all(v=='suspended' for v in d['camera_pm'].values())
assert all(d[k] for k in ['candidates_absent','m2m_video_absent','m2m_media_absent','temporary_firmware_absent'])
assert d['static_icp_status']=='disabled' and len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert not any(any(row[k] for k in ['worker','collector','client']) for row in d['workers'])
assert all(len(pids)==1 for pids in d['services'].values())
report=dict(stage=388,source_commit=state['commit'],source_clean=True,actual_sources_and_final_patch_match=True,libcamera387_library_unchanged=True,original_sg_and_camss_notes_and_files_restored=True,guard378_verified=True,candidate_permanently_installed=False,ssc_issue_not_fixed=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
