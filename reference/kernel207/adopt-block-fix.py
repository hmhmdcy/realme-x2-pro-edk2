from pathlib import Path
import difflib, hashlib, host, json, shutil
here = Path(__file__).resolve().parent
repo = here.parents[1]
proof = json.loads((host.PRIVATE / 'test-rollover-native-host-private.log').read_text())
assert proof['cases']['old-write']['expected_failure_reproduced'] and proof['cases']['old-read']['expected_failure_reproduced']
assert proof['cases']['new-rollover']['wire_block_zero_events'] == 4 and proof['test_servers_terminal']
(here / 'block-control-validation.json').write_text(json.dumps(proof, indent=2) + '\n')
radio = repo / 'linux-port/radio'
backup = host.PRIVATE / 'radio-source-before-private'; backup.mkdir(mode=0o700)
for name in ['tqftpserv-work-files.patch', 'source-lock.json']:
    shutil.copyfile(radio / name, backup / name)
lock = json.loads((radio / 'source-lock.json').read_text())
assert lock['patched_server_source_sha256'] == '20b9d630ffdf89d7fae4c19ce25710c87fd36dde3ac850eb9bc1eed6f45c04eb'
original = (host.PRIVATE.parent / 'kernel88/tqftpserv/tqftpserv.c.before').read_text()
candidate = (host.PRIVATE / 'block-rollover/tqftpserv.c').read_text()
assert hashlib.sha256(original.encode()).hexdigest() == 'bb15a562d036fc49055145a248a9a126d305ed0bbbbf79768d47ea957d92982d'
assert hashlib.sha256(candidate.encode()).hexdigest() == '5bdb6ef75af723cad63aac1511cdcaae6bfc8113749383bebea13d50b2b5103a'
(radio / 'tqftpserv-work-files.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile='a/tqftpserv.c', tofile='b/tqftpserv.c')))
lock['patched_server_source_sha256'] = hashlib.sha256(candidate.encode()).hexdigest()
lock['own_sources']['tqftpserv-work-files.patch'] = hashlib.sha256((radio / 'tqftpserv-work-files.patch').read_bytes()).hexdigest()
(radio / 'source-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
print('Native old/new control passed; full upstream patch and source lock updated, previous source preserved.')
