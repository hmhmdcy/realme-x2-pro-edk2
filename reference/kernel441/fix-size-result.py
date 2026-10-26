from pathlib import Path
import hashlib,json,subprocess
import storage
HERE=Path(__file__).resolve().parent;k=storage.mount.mounted_build().parent/'source354';rel='drivers/media/platform/qcom/camss/camss-icp-a5-ipe.c';p=k/rel
def git(*args):return subprocess.check_output(['git','-C',str(k),*args],text=True)
assert git('rev-parse','HEAD').strip()=='59b620edf17dd25074810d0d2b08951525468a74' and not git('status','--porcelain')
prototype=(HERE/'pd10-striping.c').read_text();old=prototype.replace('\tif (!bytes)\n\t\treturn -EINVAL;\n','',1)
text=p.read_text();assert text.endswith(old);p.write_text(text[:-len(old)]+prototype)
subprocess.run(['git','-C',str(k),'diff','--check'],check=True);subprocess.run(['git','-C',str(k),'add','--',rel],check=True);subprocess.run(['git','-C',str(k),'commit','-m','media: camss: reject null PD10 geometry size result'],check=True,capture_output=True)
state=json.loads((HERE/'kernel-source-state.json').read_text());state.update(commit=git('rev-parse','HEAD').strip(),initial441_commit='59b620edf17dd25074810d0d2b08951525468a74',null_size_result_rejected=True)
for row in state['source_hashes']:row['sha256']=hashlib.sha256((k/row['path']).read_bytes()).hexdigest()
(HERE/'kernel-source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'variable-pd10-kernel.patch').write_text(git('diff',state['parent_commit'],'HEAD'))
print(json.dumps({'stage':441,'commit':state['commit'],'null_result_guard_added':True,'phone_accessed':False,'passed':True}))
