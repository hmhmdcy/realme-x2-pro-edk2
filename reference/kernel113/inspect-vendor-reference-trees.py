from pathlib import Path
import json,urllib.request,urllib.parse

out=Path('/mnt/e/edk2-samurai-out/kernel113/vendor-reference-trees-private')
out.mkdir(exist_ok=True)
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
reports=[]
for repo in ('arnodorian-r/vendor_dump_RMX1931','AndroidBlobs/vendor_realme_RMX1931'):
    def get(endpoint):
        request=urllib.request.Request('https://api.github.com/repos/'+repo+'/'+endpoint,
            headers={'User-Agent':'samurai-linux-readonly-reference','Accept':'application/vnd.github+json'})
        with urllib.request.urlopen(request,timeout=25) as response:
            raw=response.read(12*1024*1024+1)
        assert len(raw)<=12*1024*1024
        return json.loads(raw)
    metadata=get('')
    branch=metadata['default_branch']
    commit=get('commits/'+urllib.parse.quote(branch,safe=''))
    tree=get('git/trees/'+commit['commit']['tree']['sha']+'?recursive=1')
    assert not tree['truncated']
    name=repo.replace('/','-')
    (out/(name+'-tree.json')).write_text(json.dumps(tree)+'\n')
    sensor=[entry for entry in tree['tree'] if entry['type']=='blob' and
            ('/sensors/' in '/'+entry['path'] or entry['path'].endswith('/sns_reg_config'))]
    config=[entry for entry in sensor if entry['path'].endswith('.json') and '/config/' in entry['path']]
    report=dict(repository=repo,commit=commit['sha'],default_branch=branch,
        sensor_files=len(sensor),config_json_files=len(config),
        selected_driver_config_names=[entry['path'].rsplit('/',1)[-1] for entry in config
            if any(part in entry['path'].lower() for part in ('lsm6','mmc560','stk333'))],
        source='third-party same-model vendor dump; not official Realme distribution',
        firmware_or_calibration_deployed=False)
    reports.append(report)
    print(json.dumps(report))
(ref/'vendor-reference-trees.json').write_text(json.dumps(reports,indent=2)+'\n')
