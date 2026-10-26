from pathlib import Path
import json,urllib.parse
import host
servers=json.loads((host.PRIVATE/'assistance-data-private/servers-private.json').read_text())
assert servers and all(not p.query and not p.fragment and not p.username and not p.password for p in map(urllib.parse.urlsplit,servers))
path=Path(__file__).resolve().parent/'assistance-download-validation.json';record=json.loads(path.read_text())
record.update(advertised_urls_have_no_query_or_credentials=True,global_assistance_download_only=True)
path.write_text(json.dumps(record,indent=2)+'\n');print('Advertised assistance URLs have no query, fragment, or credentials')
