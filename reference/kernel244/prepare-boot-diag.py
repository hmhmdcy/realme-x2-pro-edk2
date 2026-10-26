"""Generate a modem-only startup diagnostic client from the reviewed transport."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;s=(R/'diag_transport.py').read_text()
s=s.replace('self.deleted_peers=[]','self.deleted_peers=[];self.diag_ids={};self.mode_enabled=False')
s=s.replace('mask=remote&0x2051','mask=remote&0xa053')
s=s.replace('  # Only transport support bits, deliberately omit master masks and DIAG_ID.','  # Upstream master mask ownership and DIAG_ID v1, plus transport bits.')
old="      self.negotiate(peer,int.from_bytes(body[4:],'little'),n,'fresh_modem_feature')\n     offset=end"
new="""      self.negotiate(peer,int.from_bytes(body[4:],'little'),n,'fresh_modem_feature')
     elif command==33:
      if not self.sent_features or not (self.feature_mask&0x8000):raise ValueError('Unexpected DIAG_ID')
      if len(body)<9:raise ValueError('Short DIAG_ID')
      version,proposed=struct.unpack_from('<II',body);name=body[8:]
      if version!=1 or not name.endswith(b'\\0') or b'\\0' in name[:-1] or len(name)>128:raise ValueError('Unsupported DIAG_ID v1')
      if name not in self.diag_ids:self.diag_ids[name]=len(self.diag_ids)+2
      assigned=self.diag_ids[name];reply=struct.pack('<IIII',33,8+len(name),1,assigned)+name
      self.sockets[0].sendto(reply,peer);self.tx_control+=1;self.record('diag_id_assigned',diag_id=assigned,process_name_bytes=len(name))
     offset=end"""
assert old in s;s=s.replace(old,new)
needle=' def close(self):\n'
replacement=""" def diagnostic_mode(self,enabled):
  if not self.control_peer:raise RuntimeError('No live control peer')
  payload=struct.pack('<11I',3,36,1,int(enabled),int(enabled),0,0,0,0,0,0)
  self.sockets[0].sendto(payload,self.control_peer);self.tx_control+=1;self.mode_enabled=bool(enabled)
  self.record('temporary_diagnostic_realtime_mode',enabled=bool(enabled))
 def close(self):
"""
assert needle in s;s=s.replace(needle,replacement)
s=s.replace('  for i,instance in self.published:',"  if self.mode_enabled:\n   try:self.diagnostic_mode(False)\n   except Exception as e:errors.append(getattr(e,'errno',type(e).__name__))\n  for i,instance in self.published:")
compile(s,'diag_transport_boot.py','exec');(R/'diag_transport_boot.py').write_text(s)
spec=importlib.util.spec_from_file_location('diagboot',R/'diag_transport_boot.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result=m.regression()
print(json.dumps(dict(stage=244,boot_library_generated=True,regression=result,control_commands_only=[8,9,3,33],no_nv_commands=True)))
