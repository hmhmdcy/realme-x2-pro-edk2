"""Fetch official chip documentation; save locally and extract selected text."""
from pathlib import Path
import concurrent.futures, hashlib, json, re, shutil, subprocess, urllib.request
OUT = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research')
SOURCES = {
 'mps-product': 'https://www.monolithicpower.com/en/mp2650.html',
 'mps-datasheet': 'https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/document_id/9664/',
 'ti-product': 'https://www.ti.com/product/BQ28Z610',
}
def fetch(item):
    name,url = item
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as response:
            raw = response.read(8 * 1024 * 1024)
            content_type = response.headers.get('Content-Type')
        pdf = raw.startswith(b'%PDF-')
        path = OUT/(name+('.pdf' if pdf else '.html'))
        path.write_bytes(raw)
        row = {'name':name,'url':url,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'content_type':content_type,'pdf':pdf}
        if pdf and shutil.which('pdftotext'):
            text_path = path.with_suffix('.txt')
            subprocess.run(['pdftotext','-layout',str(path),str(text_path)],check=True,timeout=20)
            text = text_path.read_text(errors='replace')
        else:
            text = re.sub(r'<[^>]+>',' ',raw.decode(errors='replace'))
        lines = text.splitlines()
        row['matches'] = [l.strip()[:500] for l in lines if re.search(r'watchdog|safety timer|thermistor|NTC|temperature.*monitor|[12].?(?:cell|series)|2.to.4|buck.boost|buck or boost|MP2650|bq28z610',l,re.I)][:28]
        return row
    except Exception as exc:
        return {'name':name,'url':url,'error':str(exc)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results=list(pool.map(fetch,SOURCES.items()))
(OUT/'official-chip-documents.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
