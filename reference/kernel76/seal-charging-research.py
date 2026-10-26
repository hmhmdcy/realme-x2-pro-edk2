"""Create a compact provenance record for the completed read-only investigation."""
from pathlib import Path
import datetime, hashlib, json, subprocess

REF = Path(__file__).resolve().parent
OUT = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research')
heads = json.loads((OUT/'repository-heads.json').read_text())
rows = []
for path in sorted(OUT.glob('source-tasks*.results.json')):
    for row in json.loads(path.read_text()):
        if row.get('error'):
            continue
        data = (OUT/row['saved']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        record = {k:row[k] for k in ('name','path','kind','url','commit','bytes','sha256')}
        if row['kind'] == 'tree':
            children = sorted({x['path'] for x in row['items'] if x.get('path','').rsplit('/',1)[0] == row['path']})
            record['child_count'] = len(children)
            if row['name'] == 'mainline' and row['path'] == 'drivers/power/supply':
                record['mp26_children'] = [p for p in children if 'mp26' in p.lower()]
        rows.append(record)
related_count = len(rows)
vendor_commit = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
vendor_repo = '/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git'
stock_manifest = json.loads((REF/'stock-source-manifest.json').read_text())
comparison = json.loads((OUT/'source-comparison.json').read_text())
stock_paths = set(stock_manifest['files']) | {r['path'] for r in comparison['stock'] if 'sha256' in r}
stock_paths.add('arch/arm64/boot/dts/19781/pm8150b.dtsi')
for path in sorted(stock_paths):
    raw = subprocess.check_output(['git', '--git-dir='+vendor_repo, 'cat-file', '-p', vendor_commit+':'+path])
    digest = hashlib.sha256(raw).hexdigest()
    if path in stock_manifest['files']:
        assert digest == stock_manifest['files'][path]['sha256']
    previous = next((r for r in comparison['stock'] if r['path'] == path), None)
    if previous and 'sha256' in previous:
        assert digest == previous['sha256']
    rows.append({'name':'realme', 'path':path, 'kind':'git-blob',
                 'url':'https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/'+vendor_commit+'/'+path,
                 'commit':vendor_commit, 'bytes':len(raw), 'sha256':digest})
archive = Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
manifest = {'retrieved_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope':'Read-only source/archived-DT investigation. No phone or kernel modifications.',
            'repository_heads':[{k:v for k,v in r.items() if k in ('name','repo','url','oid','branch')} for r in heads],
            'sources':rows,
            'stock_dt_archive':{'captured_at_utc':'2026-10-05T07:49:31Z', 'bytes':archive.stat().st_size,
                                'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},
            'official_chip_documents':[
                {'title':'MP2650 datasheet', 'revision':'1.0, 2022-04-22',
                 'url':'https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/document_id/9664/',
                 'reviewed_pages':[27,35,36,43,44], 'retrieval':'web PDF reader; full PDF not republished'},
                {'title':'BQ28Z610 Technical Reference Manual', 'revision':'SLUUA65E, June 2023',
                 'url':'https://www.ti.com/lit/ug/sluua65e/sluua65e.pdf',
                 'reviewed_sections':['12.1.4 Temperature', '12.1.5 Voltage', '12.1.7 Current'],
                 'retrieval':'web PDF reader; full PDF not republished'}],
            'limitations':['Initial web.run and Firecrawl transport calls failed; both recovered on retry during this investigation. Direct public GitHub HTML/raw source retrieval also succeeded.',
                           'GitHub anonymous API was rate limited. Windows and WSL gh auth status both reported invalid existing tokens; no credentials or login configuration were changed.',
                           'Google responses were JavaScript landing pages, not usable search results.',
                           'Direct Python MPS requests returned access-challenge HTML; the official 66-page MP2650 PDF was subsequently read successfully with the web PDF reader.',
                           'Selected OnePlus default Android 9 branch; other branches were not exhaustively searched.',
                           'DT nodes alone do not prove physical chip presence or successful driver binding.']}
(REF/'charging-source-provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
safety = json.loads((OUT/'local-safety-inspection.json').read_text())
facts = {'vendor_commit':safety['vendor_commit'], 'live_nodes':comparison['live'],
         'scope':'Archived Android DT from 2026-10-05; these are not current Linux measurements or recommended charging limits.',
         'live_policy':safety['live_policy'], 'live_pin_handles':safety['live_pin_handles'],
         'upstream_config':safety['power_config'], 'local_smbx_matches':comparison['upstream_smbx']}
(REF/'charging-stock-runtime-facts.json').write_text(json.dumps(facts,indent=2)+'\n')
print(json.dumps({'verified_public_sources':len(rows), 'related_and_mainline_sources':related_count,
                  'realme_sources':len(stock_paths), 'live_nodes':len(facts['live_nodes']),
                  'policy_properties':len(facts['live_policy'])}))
