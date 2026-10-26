"""Publish the source-only fast-forward after verifying the existing branch head."""
from pathlib import Path
import json,subprocess,os
R=Path(__file__).resolve().parent;U=Path('/home/cy122/x2pro-linux/upstream')
G=['git','-c','safe.directory='+str(U),'-C',str(U)]
def git(*args):return subprocess.check_output(G+list(args),text=True).strip()
d=json.loads((R/'kernel-commit-validation.json').read_text());old=json.loads((R/'maintained-source-validation.json').read_text())['before_head']
assert not git('status','--porcelain') and git('rev-parse','HEAD')==d['commit']
remote=git('ls-remote','origin','refs/heads/samurai-bringup').split()[0];assert remote==old,'Remote changed; preserve and inspect it'
env=dict(os.environ,GIT_TERMINAL_PROMPT='0')
log=Path('/mnt/e/edk2-samurai-out/kernel268/push-gh-http11-private.log')
with log.open('xb') as output:
 result=subprocess.run(G+['-c','credential.helper=','-c','credential.helper=!gh auth git-credential',
  '-c','http.version=HTTP/1.1','-c','http.lowSpeedLimit=1000','-c','http.lowSpeedTime=30',
  '-c','http.postBuffer=1048576','push','origin','HEAD:refs/heads/samurai-bringup'],env=env,stdout=output,stderr=subprocess.STDOUT,timeout=65)
assert git('ls-remote','origin','refs/heads/samurai-bringup').split()[0]==d['commit']
report=dict(stage=268,repository=d['repository'],branch=d['branch'],commit=d['commit'],remote_head_verified=True,
 fast_forward_only=True,source_only_files=14,upstream_acceptance_not_claimed=True,git_push_exit_code=result.returncode)
(R/'kernel-publication-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
