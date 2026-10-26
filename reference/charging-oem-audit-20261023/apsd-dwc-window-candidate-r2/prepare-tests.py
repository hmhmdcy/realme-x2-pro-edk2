"""Extract actual changed functions for a fake-OS boundary test, not a model."""
from pathlib import Path
import hashlib
import importlib.util
import json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('candidate_functions',HERE/'make-candidate.py')
make=importlib.util.module_from_spec(spec);spec.loader.exec_module(make)
targets={'core.h':['dwc3_gadget_window_busy'],
 'gadget.c':['dwc3_gadget_window_wanted','dwc3_gadget_window_result_locked','dwc3_gadget_window_park_locked',
  'dwc3_gadget_window_begin','dwc3_gadget_window_cancel','dwc3_gadget_window_end','dwc3_gadget_window_shutdown',
  'dwc3_gadget_pullup','dwc3_gadget_recover_locked','dwc3_err_recovery_work',
  'dwc3_gadget_suspend','dwc3_gadget_resume','dwc3_gadget_start','dwc3_gadget_stop','dwc3_gadget_exit'],
 'core.c':['dwc3_gadget_window_pm_enter','dwc3_gadget_window_pm_exit','dwc3_pm_prepare','dwc3_pm_complete']}
rows=[];bodies=[]
for path,names in targets.items():
 text=(HERE/path).read_text()
 for name in names:
  body=make.function(text,name)
  rows.append(dict(function=name,file=path,line=text[:text.index(body)].count('\n')+1,
                   sha256=hashlib.sha256(body.encode()).hexdigest()))
  bodies.append(body)
h=(HERE/'core.h').read_text();types=h[h.index('enum dwc3_gadget_window_state {'):h.index('/**\n * struct dwc3 -')]
(HERE/'tested-types.inc').write_text(types)
(HERE/'tested-functions.inc').write_text('static int dwc3_gadget_recover_locked(struct dwc3 *dwc);\n\n'+'\n\n'.join(bodies)+'\n')
(HERE/'tested-functions.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'actual_functions':len(rows)}))
