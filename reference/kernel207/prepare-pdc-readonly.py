from pathlib import Path
import ast, host, json
here = Path(__file__).resolve().parent
for oldname, newname in [('query-pdc-readonly.py', 'query-pdc-readonly.py'), ('query-pdc-details.py', 'query-pdc-details.py')]:
    source = (here.parent / 'kernel206' / oldname).read_text().replace('k205r2-runtime', 'k207-runtime').replace('k206', 'k207').replace('stage=206', 'stage=207')
    ast.parse(source); (here / newname).write_text(source)
print('Prepared fresh-boot read-only PDC queries, with the already validated optional-TLV handling.')
