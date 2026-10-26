from pathlib import Path
here=Path(__file__).resolve().parent
text=(here.parent/'kernel221/final-health.py').read_text().replace("out=root/'k221-final-health'","out=root/'k222-final-health'").replace('k221-baseline/boot-id-private.txt','k222-baseline/boot-id-private.txt').replace("root/'k221-baseline/modem-path-private.txt'","root/'k221-baseline/modem-path-private.txt'").replace('stage=221','stage=222')
start=text.index('tools=[]');end=text.index('r=dict(stage=222',start)
replacement=r'''trials=[]
for name,phase in [('k222-sof-trial','original-restored'),('k222-sof-trial-r2','verified-restored')]:
 r=json.loads((root/name/'state-private.json').read_text());assert r['phase']==phase and all(x['exit']==0 for x in r['commands']);trials.append(name)
import struct,fcntl
camss=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/platform/qcom/camss/qcom-camss.ko'
data=camss.read_bytes();assert hashlib.sha256(data).hexdigest()=='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58'
offset=struct.unpack_from('<Q',data,40)[0];size,count,strings=struct.unpack_from('<HHH',data,58);hs=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];s=hs[strings];names=data[s[4]:s[4]+s[5]]
notes=[data[h[4]:h[4]+h[5]] for h in hs if names[h[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id'];assert len(notes)==1 and notes[0]==Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()
nodes={(p/'name').read_text().strip():p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*')}
fd=os.open('/dev/'+nodes['msm_vfe0_rdi0'],os.O_RDWR|os.O_CLOEXEC)
try:
 sub=bytearray(32);struct.pack_into('I',sub,0,4)
 try:fcntl.ioctl(fd,0x4020565a,sub,True);raise AssertionError('Original driver unexpectedly exposes candidate events')
 except OSError as error:assert error.errno in [22,25]
finally:os.close(fd)
for name in ['imx471 7-0010','msm_csid0']:
 text=subprocess.check_output(['v4l2-ctl','-d','/dev/'+nodes[name],'--get-ctrl=test_pattern'],text=True,timeout=10);assert re.search(r'^test_pattern:\s*0(?:\s|\(|$)',text)
'''
replacement=replacement.replace('b\'\\\\0\'','b\'\\0\'').replace('import struct,fcntl','import struct,fcntl,re')
text=text[:start]+replacement+text[end:]
text=text.replace('readonly_tool_runs_with_complete_cleanup=len(tools)','temporary_camss_trials_restored=len(trials),original_camss_file_and_loaded_note_verified=True,candidate_frame_sync_not_left_enabled=True,test_patterns_disabled=True')
text=text.replace('no_camera_capture_or_engine_start_or_reboot=True','camera_metadata_captures_performed=True,no_gnss_engine_start_or_flash_or_reboot=True').replace('uim_slot_status_lines=slot_lines','uim_slot_status_lines_historical_stage221=slot_lines')
compile(text,'health222','exec');(here/'final-health.py').write_text(text)
archive=(here.parent/'kernel221/collect-final-evidence.py').read_text().replace('k221-','k222-').replace('stage=221','stage=222');compile(archive,'archive222','exec');(here/'collect-final-evidence.py').write_text(archive)
print('K222_NATIVE_FINAL_HEALTH_AND_EVIDENCE_COLLECTORS_PREPARED')
