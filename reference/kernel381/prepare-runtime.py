from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=HERE.parent/'kernel379'
s=(OLD/'boot-worker.py').read_text().replace("['fw','shared','heap','trace']","['fw','shared','heap','trace','images']")
s=s.replace('owned_firmware=False','owned_firmware=False',1)
anchor="collector=None;collector_log=None;cleanup_attempted=False";assert s.count(anchor)==1
s=s.replace(anchor,"extra_firmware=[]\n"+anchor)
s=s.replace("not result.get('remaining_domains')","not result.get('remaining_domains') and not result.get('ipe_dma_pending') and not result.get('request_fw_mapped')")
anchor=" save('load-core');run(['insmod',str(ROOT/'core.ko')]);owned_core=True";assert s.count(anchor)==1
s=s.replace(anchor," for source,name in [('ipe-stripe.bin','samurai-ipe381-stripe.bin'),('ipe-iq.bin','samurai-ipe381-iq.bin')]:\n  target=firmware.parent/name\n  with target.open('xb') as stream:\n   extra_firmware.append(target);stream.write((ROOT/source).read_bytes());stream.flush();os.fsync(stream.fileno())\n"+anchor)
anchor="'snapshot_words='+','.join(str(w['words']) for w in meta['snapshot_profile']['windows'])])";assert s.count(anchor)==1
s=s.replace(anchor,"'snapshot_words='+','.join(str(w['words']) for w in meta['snapshot_profile']['windows']),'enable_frame=1'])")
anchor=" assert Path('/sys/module',test,'parameters/bound_seen')";assert s.count(anchor)==1;s=s.replace(anchor," assert ready_result.get('engine_dma_capable'),'Combined ICP SID ownership is required before frame dispatch'\n"+anchor)
s=s.replace(" if not result.get('cpu_release_attempted') or not result.get('error'):"," if not held and releasable(result):")
s=s.replace(" and result.get('image_frames')==0)",")")
anchor=" observation['passed']=handshake and sessions and io";assert s.count(anchor)==1
s=s.replace(anchor," frame=bool(result.get('image_frames')==1 and result.get('frames_completed')==1 and result.get('transfer_maps')==1 and result.get('transfer_unmaps')==1 and result.get('ipe_reset_acks')==[3,3] and result.get('engine_dma_capable') and not result.get('ipe_dma_pending') and not result.get('request_fw_mapped') and result.get('image_bytes')==460800)\n observation['image_control_completion_passed']=frame\n"+anchor+' and frame')
anchor="   (ROOT/'sfr-private.txt').write_text";assert s.count(anchor)==1
s=s.replace(anchor,"   if result.get('frames_completed')==1 and result.get('image_bytes')==460800 and not result.get('error'):\n    image=Path('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/image').read_bytes();assert len(image)==460800\n    with (ROOT/'ipe-output-private.nv12').open('xb') as stream:stream.write(image);stream.flush();os.fsync(stream.fileno())\n"+anchor)
anchor="  if owned_firmware and not Path('/sys/module',test).exists():firmware.unlink();owned_firmware=False";assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n  if not Path('/sys/module',test).exists():\n   for path in extra_firmware:path.unlink()\n   extra_firmware=[]")
s=s.replace("not owned_firmware and not firmware.exists()","not owned_firmware and not firmware.exists() and not extra_firmware and not any((firmware.parent/name).exists() for name in ['samurai-ipe381-stripe.bin','samurai-ipe381-iq.bin'])")
(HERE/'boot-worker.py').write_text(s)
(HERE/'snapshot-collector.py').write_bytes((OLD/'snapshot-collector.py').read_bytes())
(HERE/'firmware-context-validation.json').write_bytes((OLD/'firmware-context-validation.json').read_bytes())
s=(OLD/'launch-boot.py').read_text().replace('stage=379','stage=381').replace('k379-boot-','k381-boot-').replace('Prepared379','Prepared381')
old="['hal-io','firmware-io','encoder','session','owner','dispatch','worker','intree-build']";new="['ipe-quiesce','ipe-sids','transfer','overlay','session','owner','dispatch','worker','intree-build']";assert s.count(old)==1;s=s.replace(old,new)
anchor="'worker.py':HERE/'boot-worker.py'";assert s.count(anchor)==1
s=s.replace(anchor,"'ipe-stripe.bin':P.parent/'kernel380/640x480-port8-cores1-stripe-private.bin','ipe-iq.bin':P.parent/'kernel380/640x480-port8-cores1-iq-private.bin',\n "+anchor)
(HERE/'launch-boot.py').write_text(s)
s=(OLD/'poll-boot.py').read_text().replace('stage=379','stage=381').replace('k379-boot-','k381-boot-')
s=s.replace("['collector-ready.json'","['ipe-output-private.nv12','collector-ready.json'").replace("keys=['ipe_io_config_passed'","keys=['image_control_completion_passed','ipe_io_config_passed'")
(HERE/'poll-boot.py').write_text(s)
s=(OLD/'preflight.py').read_text().replace('stage=379','stage=381').replace('k379-boot-','k381-boot-')
s=s.replace("assert args[3]=='snapshot_offsets='","assert args[5]=='enable_frame=1'\nassert args[3]=='snapshot_offsets='")
s=s.replace(" camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status')", " extra_firmware_absent=not any(Path('/lib/firmware/qcom/sm8150',name).exists() for name in ['samurai-ipe381-stripe.bin','samurai-ipe381-iq.bin']),\n camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status')")
s=s.replace("and d['camss']=='suspended'", "and d['extra_firmware_absent'] and d['camss']=='suspended'")
(HERE/'preflight.py').write_text(s)
# Unit harnesses exercise the changed owner and worker blocks, not firmware.
s=(OLD/'check-owner.py').read_text().replace('stage=379','stage=381').replace('33,34,35]','33,34,35,36]');(HERE/'check-owner.py').write_text(s)
s=(OLD/'owner-regression.c').read_text().replace('static int test_lock,test_error;','static int test_lock,test_error;static bool enable_frame=true;\nstatic int test_frame(struct device *d,struct camss_a5 *a){(void)d;(void)a;return scenario==36?-EREMOTEIO:0;}')
# scenario is needed before the helper declaration.
s=s.replace('static int test_lock,test_error;static bool enable_frame=true;','static int scenario;static int test_lock,test_error;static bool enable_frame=true;').replace('static int scenario;static bool get_ok=true;','static bool get_ok=true;')
(HERE/'owner-regression.c').write_text(s)
s=(OLD/'check-worker.py').read_text().replace('stage=379','stage=381').replace('image_frames=0,error=0','image_frames=1,frames_completed=1,transfer_maps=1,transfer_unmaps=1,ipe_reset_acks=[3,3],engine_dma_capable=True,ipe_dma_pending=False,request_fw_mapped=False,image_bytes=460800,error=0')
s=s.replace("and observation['passed']","and observation['image_control_completion_passed'] and observation['passed']")
s=s.replace('import copy,json,tempfile,time','import copy,json,os,tempfile,time').replace('Path=path,json=json,time=time','Path=path,json=json,os=os,time=time')
s=s.replace(" def path(value):\n  assert value==", " def path(value):\n  if value=='/sys/bus/platform/devices/ac10000.samurai-icp356-boot/image':\n   assert case=='ready'\n   return type('Image',(),{'read_bytes':lambda self:b'\\x7c'*460800})()\n  assert value==")
s=s.replace(" rows.append(dict(case=case,", " if case=='ready':assert (root/'ipe-output-private.nv12').read_bytes()==b'\\x7c'*460800\n rows.append(dict(case=case,")
(HERE/'check-worker.py').write_text(s)
s=(OLD/'check-dispatch.py').read_text().replace('stage=379','stage=381').replace('for case in range(9):','for case in range(10):').replace("ready=dict(terminal=True,","ready=dict(engine_dma_capable=True,terminal=True,")
s=s.replace(" if case==8:state['error']=-5"," if case==8:state['error']=-5\n if case==9:state['engine_dma_capable']=False")
(HERE/'check-dispatch.py').write_text(s)
for path in [HERE/'boot-worker.py',HERE/'launch-boot.py',HERE/'poll-boot.py',HERE/'check-owner.py',HERE/'owner-regression.c',HERE/'check-worker.py',HERE/'check-dispatch.py']:
 if path.suffix=='.py':compile(path.read_text(),str(path),'exec')
print('Prepared unique synthetic frame transaction, strict engine gate, private output collection and extended cleanup models.')
