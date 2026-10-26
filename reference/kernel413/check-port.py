"""Recheck changed portable math against retained, unchanged target records."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
report=json.loads((HERE/'generation-validation.json').read_text())
inputs=(P/'generation-input-private.bin').read_bytes();wanted=(P/'generation-expected-private.bin').read_bytes()
assert len(inputs)==(report['cases']+12)*9408 and len(wanted)==(report['cases']+12)*8292
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss413-generation'
files=[r['path'] for r in report['current_source_hashes']]
for name in files:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror'];rels=[n for n in files if n.endswith('.cpp')]
    if arch=='host':
        binary=P/'generation-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss413-generation/generation-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss413-generation/'+n for n in rels],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/(arch+'-generation-actual-private.bin')).write_bytes(q.stdout);assert len(q.stdout)==len(wanted)
    diffs=sum(a!=b for a,b in zip(q.stdout,wanted));rows.append(dict(architecture=arch,cases=report['cases'],invalid_cases=12,compared_bytes=len(wanted),different_bytes=diffs,passed=not diffs));print(json.dumps(rows[-1]),flush=True)
report.update(architectures=rows,retained_original_target_records_reused_after_port_change=True,
    finite_dark_knee_quotient_not_clipped_to_second_anchor=True,
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in files],passed=all(r['passed'] for r in rows))
(HERE/'generation-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['passed']
