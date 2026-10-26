"""Add PIX/FULL topology semantics to the frozen 459 lifecycle helper."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
role=load('role463',HERE/'full-role.py')
original=HERE.parent/'kernel459/trace-instance.py'
assert hashlib.sha256(original.read_bytes()).hexdigest()=='1327a362ce7da46a0c208c1bd1466b782e1c8e8f6d480ac3e6247706e9b35023'
base=load('trace459_guarded',original)

class GuardedPlan(base.Plan):
 def __init__(self,probe_bytes,selection_bytes,extra_bytes,graph_bytes):
  selection=json.loads(selection_bytes)
  role.require(selection.get('full_role_graph_sha256')==role.sha(graph_bytes),'selection lacks this graph binding')
  self.full_role=role.discover(probe_bytes,graph_bytes,selection.get('pixel_entity',''))
  role.check_selection(self.full_role,selection)
  super().__init__(probe_bytes,selection_bytes,extra_bytes)
  self.key=role.sha(base.packed(dict(base_key=self.key,full_role=self.full_role)))
 def render(self,action,evidence):
  result=super().render(action,evidence)
  result.update(full_role=self.full_role,live_fd_and_event_witness_required_before_acceptance=True)
  return result

# Lifecycle implementation is reused unchanged, including ownership and cleanup.
Session=base.Session
RealFiles=base.RealFiles
