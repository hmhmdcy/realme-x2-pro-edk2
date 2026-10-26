from pathlib import Path
from hashlib import sha256
import gzip,json

root=Path(__file__).resolve().parent
out=Path('/mnt/e/RealmeX2Pro edk2/reference/rx57');out.mkdir(parents=True,exist_ok=True)
rows=[]
def export(src,name=None,exact=False):
    original=src.read_bytes();name=name or src.name;data=original
    if not exact:data='\n'.join(s.rstrip() for s in original.decode('utf-8-sig').splitlines()).encode()+b'\n'
    (out/name).write_bytes(data)
    rows.append(dict(name=name,original=str(src),original_sha256=sha256(original).hexdigest(),exported_sha256=sha256(data).hexdigest(),byte_identical=(data==original)))
for folder,prefix in [('logging-audit','logging'),('creation-audit','creation')]:
    for src in sorted((root/folder).glob('*.asm.txt')):export(src)
    export(root/folder/'qcusbser-identity.json',prefix+'-identity.json')
export(root.parent/'rx54/driver-audit/QCMRD_L2MultiReadThread.asm.txt')
for name in ['driver-log-admin.ps1','capture-windows.ps1','launch-approved-logger.ps1','test-prepared.ps1',
             'driver-log-admin-02.ps1','capture-windows-02.ps1','launch-approved-logger-02.ps1','test-prepared-02.ps1',
             'prepare-retry.py','parse-driver-log.py','test-driver-log.py','parse-captured-logs.py','analyze-capture.py',
             'audit-logging-config.py','audit-etw-outstanding.py','capture-state.ps1','export-evidence.py']:
    export(root/name,exact=True)
for name in ['logging-plan.json','logging-plan-02.json','prepared-hashes.json','prepared-hashes-02.json',
             'prepared-tests.json','prepared-tests-02.json','parser-tests.json','logging-code-refs.json',
             'config-copy-window.json','etw-outstanding.json','focused-research.json','admin-launch.json',
             'admin-launch-02.json','state-after-attempt-01.json','final-state.json','capture-summary.json',
             'logging-capture-plan.md','logging-capture-plan-02.md']:
    export(root/name,exact=True)
for attempt in ['01','02']:
    for name in ['backup.json','status.json']:
        export(root/('control-'+attempt)/name,'control-'+attempt+'-'+name,exact=True)
for name in ['windows-log-02.raw','windows-log-02.txt','windows-log-02.events.txt','windows-log-02.rx-audit.jsonl','windows-tx-journal.bin']:
    export(root/name,exact=True)
for src in sorted((root/'driver-logs-02').glob('*.log')):export(src,exact=True)
deps=['../rx55/EudRxAudit.cs','../rx55/EudSerialPerf.cs','../rx55/eud-terminal-rx-perf.ps1','../rx55/analyze-windows-perf.py','../rx55/windows-perf-01.raw',
      '../rx56/QCSER_VendorRegistryProcess.asm.txt','../rx56/QCSER_PostVendorRegistryProcess.asm.txt','../rx56/QCSER_LogData.asm.txt',
      '../rx56/front-identity.json','../rx56/old-etw-target-transfers.json.gz','../rx54/installed-driver-identity.json','../rx53/source-epoch.json']
(out/'dependencies.json').write_text(json.dumps({n:sha256((out/n).read_bytes()).hexdigest() for n in deps},indent=2)+'\n')
(out/'exports.json').write_text(json.dumps(rows,indent=2)+'\n')
(out/'.gitattributes').write_text('*.py -text\n*.ps1 -text\n*.raw binary\n*.bin binary\n*.log binary\n*.txt -text\n*.json -text\n*.jsonl -text\nlogging-capture-plan*.md -text\n')
print('Exported',len(rows),'files; diagnostics reused from RX55. No full sys/PDB, unrelated-device trace, image or test fixture exported.')
