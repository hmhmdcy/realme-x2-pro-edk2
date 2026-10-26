from pathlib import Path

here = Path(__file__).resolve().parent
s = (here / 'final-health.py').read_text()
s = s.replace("out=root/'k226-final-health'", "out=root/'k226-post-aiding-health'")
s = s.replace("for kind in ['default','high']:", "for kind in ['default','high','default-aided','high-aided']:")
s = s.replace("(host.PRIVATE / 'final-health-host-private.log')", "(host.PRIVATE / 'post-aiding-health-host-private.log')")
s = s.replace("(here / 'final-health-validation.json')", "(here / 'post-aiding-health-validation.json')")
(here / 'post-aiding-health.py').write_text(s)
s = (here / 'collect-final-evidence.py').read_text()
s = s.replace('final-health-validation.json', 'post-aiding-health-validation.json')
s = s.replace('final-evidence-private.tar.gz', 'final-evidence-aided-private.tar.gz')
s = s.replace('final-evidence-manifest-private.json', 'final-evidence-aided-manifest-private.json')
s = s.replace('final-evidence-validation.json', 'final-evidence-aided-validation.json')
needle="target=Path('/tmp/k226-final-evidence-aided-private.tar.gz');assert not target.exists()"
assert needle in s
addition="""
aid=root/'k226-assistance-refresh'
result=json.loads((aid/'result-private.json').read_text())
assert result['status']=='refreshed' and result['download_count']==result['injection_count']==1
assert json.loads((root/'gnss-assist/last-result.json').read_text())==result
for old,new in [('candidate-0.bin','aiding-payload-private.bin'),('last-result.json','helper-last-result-private.json')]:
    source=root/'gnss-assist'/old;destination=aid/new
    assert source.is_file() and not destination.exists()
    destination.write_bytes(source.read_bytes());destination.chmod(0o600)
"""
s = s.replace(needle, needle + '\n' + addition)
(here / 'collect-aided-evidence.py').write_text(s)
s = (here / 'analyze-receiver-debug.py').read_text()
s = s.replace("'final-evidence-private.tar.gz'", "'final-evidence-aided-private.tar.gz'")
s = s.replace("['default', 'high']", "['default', 'high', 'default-aided', 'high-aided']")
s = s.replace("'receiver-debug-validation.json'", "'receiver-debug-aided-validation.json'")
(here / 'analyze-aided-receiver-debug.py').write_text(s)
print('K226_AIDED_CLOSING_SOURCES_PREPARED_NO_DEVICE_OPERATION')
