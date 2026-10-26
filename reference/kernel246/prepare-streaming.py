"""Prepare fixed streaming-mode control17, using the Android packed v1 ABI."""
from pathlib import Path
import hashlib,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel246')
s=(R.parent/'kernel245/diag_resume_rf.py').read_text().replace('No buffering configuration, NV or RF settings are sent.','Fixed stream1/streaming control17 may be sent; prior buffering state is unknown.\nNo NV or RF settings are sent.')
anchor='class Diag:\n';packet="def streaming_packet():\n return struct.pack('<IIIBB',17,6,1,1,0)\n"
assert anchor in s;s=s.replace(anchor,packet+anchor)
s=s.replace('self.mode_enabled=False\n','self.mode_enabled=False;self.streaming_sent=False\n')
anchor=' def close(self):\n'
method=" def diagnostic_streaming(self):\n  if not self.control_peer or not self.sent_features:raise RuntimeError('No negotiated control peer')\n  if self.feature_mask&0x80000:raise RuntimeError('Per-ID feature mode requires separate v2 validation')\n  if self.streaming_sent:raise RuntimeError('Streaming request already sent')\n  self.sockets[0].sendto(streaming_packet(),self.control_peer);self.tx_control+=1;self.streaming_sent=True\n  self.record('diagnostic_streaming_request',version=1,stream_id=1,tx_mode=0,previous_mode_unknown=True,no_restore_claim=True)\n"
assert anchor in s;s=s.replace(anchor,method+anchor);compile(s,'diag_streaming.py','exec');(R/'diag_streaming.py').write_text(s)
spec=importlib.util.spec_from_file_location('diag246',R/'diag_streaming.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.streaming_packet().hex()=='1100000006000000010000000100' and len(m.streaming_packet())==14
native=(R.parent/'kernel245/native-resume-rf-r4.py').read_text().replace('stage=245','stage=246').replace("o=r/'k245-resume-rf-r4'","o=r/'k246-streaming-rf'").replace("str(r/'k245-tools')","str(r/'k246-tools')").replace('from diag_resume_rf import','from diag_streaming import')
native=native.replace("d.diagnostic_mode(True);d.gnss_logs(True);run_phase('baseline-off')","assert feature['remote_mask']&0x400\n   d.diagnostic_mode(True);d.diagnostic_streaming();d.gnss_logs(True);run_phase('baseline-off')")
native=native.replace('original_features_reasserted=True,fresh_feature_handshake=False','original_features_reasserted=True,diagnostic_streaming_request_sent=d.streaming_sent,prior_buffering_mode_unknown=True,fresh_feature_handshake=False')
native=native.replace('The only optional second action is standard MM SetPowerState(ON), then GNSS.','Diagnostic streaming is explicitly configured. The optional second action is\nstandard MM SetPowerState(ON), then GNSS. Prior buffering mode is unknown.')
compile(native,'native-streaming-rf.py','exec');(R/'native-streaming-rf.py').write_text(native)
runner=(R.parent/'kernel245/run-native.py').read_text().replace("kernel245","kernel246");(R/'run-native.py').write_text(runner)
poll=(R.parent/'kernel245/poll-resume-r4.py').read_text().replace('stage=245','stage=246').replace('k245-resume-rf-r4','k246-streaming-rf');(R/'poll-streaming.py').write_text(poll)
launch=(R.parent/'kernel245/launch-resume-rf.py').read_text().replace('kernel245','kernel246').replace("['diag_resume_rf.py','native-resume-rf.py']","['diag_streaming.py','native-streaming-rf.py','loc_decode.py']").replace('k245-tools','k246-tools').replace('k245-resume-rf','k246-streaming-rf').replace('native-resume-rf.py','native-streaming-rf.py').replace("assert o.exists() and not", "assert not o.exists() and not").replace("hashes={}\n","hashes={};o.mkdir(mode=0o700)\n").replace('stage=245','stage=246').replace('resume-worker-private.log','streaming-worker-private.log').replace('launch-resume-private.log','launch-streaming-private.log').replace('resume-launch-validation.json','streaming-launch-validation.json')
compile(launch,'launch-streaming.py','exec');(R/'launch-streaming.py').write_text(launch);(R/'loc_decode.py').write_bytes((R.parent/'kernel226/loc_decode.py').read_bytes())
report=dict(stage=246,packet_hex=m.streaming_packet().hex(),packed_bytes=14,command=17,body_bytes=6,version=1,stream=1,tx_mode=0,prior_buffering_state_unknown=True,gnss_regression=m.regression(),library_sha256=hashlib.sha256(s.encode()).hexdigest(),native_sha256=hashlib.sha256(native.encode()).hexdigest())
(R/'streaming-library-validation.json').write_text(json.dumps(report,indent=2)+'\n');(P/'previous-turn-classification-private.json').write_text(json.dumps(dict(previous_stage=245,classification='progress',basis=['MT/NONE native negative control','same-boot DIAG CMD restoration, logging negative','MEMSHARE113s zero requests','active IDs equal exact source MBN SHA1'],goal_active=True),indent=2)+'\n');print(json.dumps(report))
