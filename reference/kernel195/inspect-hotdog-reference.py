from pathlib import Path
import hashlib,json,subprocess
repo=Path('/home/cy122/x2pro-linux/hotdog-ref195');out=Path('/mnt/e/edk2-samurai-out/kernel195');ref=Path(__file__).resolve().parent
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();assert commit=='47087509c4289c2580c54f5433e55366b2e00445'
files=subprocess.check_output(['git','ls-tree','-r','--name-only',commit],cwd=repo,text=True).splitlines();selected=[n for n in files if any(v in n.lower() for v in ['imx471','camera','camss','bluetooth','gnss','cci'])];(out/'hotdog-reference-paths-private.json').write_text(json.dumps(selected,indent=2)+'\n')
print(json.dumps(dict(commit=commit,total_files=len(files),selected_paths=selected),indent=2))
r=dict(stage=195,url='https://github.com/Sr-0w/hotdog-linux-bringup',commit=commit,read_only_no_checkout=True,upstream_claim_is_not_our_handset_validation=True,total_files=len(files));(ref/'hotdog-reference-validation.json').write_text(json.dumps(r,indent=2)+'\n')
