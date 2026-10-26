"""Inspect 452's prepared terminal query; --live is an explicit read-only call."""
from pathlib import Path
import argparse,ast,hashlib,json,shlex
import host,storage

parser=argparse.ArgumentParser()
parser.add_argument('--attempt',default='r1')
parser.add_argument('--handoff',type=Path,required=True)
parser.add_argument('--live',action='store_true')
args=parser.parse_args()
storage.mount.mounted_build()
assert args.attempt.startswith('r') and args.attempt[1:].isdigit() and 1<=int(args.attempt[1:])<=20
window='k452-full-diagnostic-'+args.attempt
handoff=json.loads(args.handoff.read_text())
assert handoff['window_id']==window and handoff['window_owner']=='camera' and handoff['fresh_preflight_verified'] is True
private=Path('/mnt/e/edk2-samurai-out/kernel452')
query=private/('diagnostic-prepared-'+args.attempt)/'inspect-terminal-private.py'
source=query.read_text();ast.parse(source)
assert repr('/var/lib/samurai/'+window) in source and repr(hashlib.sha256(args.handoff.read_bytes()).hexdigest()) in source
assert 'FRESH_HANDOFF_REQUIRED' in source # the runtime assertion rejects the placeholder
if not args.live:
 print(json.dumps(dict(query_validated=True,phone_accessed=False,passed=True)))
else:
 q=host.raw_ssh('python3 -B -c '+shlex.quote(source),timeout=25);q.check_returncode()
 data=json.loads(q.stdout)
 index=1
 while (private/f'diagnostic-live-{args.attempt}-{index}-private.json').exists():index+=1
 (private/f'diagnostic-live-{args.attempt}-{index}-private.json').write_bytes(q.stdout)
 print(json.dumps(data,indent=2))
