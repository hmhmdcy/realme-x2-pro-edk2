 import fcntl
 video=[str(Path('/dev')/p.parent.name) for p in Path('/sys/class/video4linux').glob('video*/name') if p.read_text().strip()=='qcom-ipe-a5'];assert len(video)==1
 media=[]
 for path in Path('/dev').glob('media[0-9]*'):
  try:
   with path.open('rb',buffering=0) as f:
    data=bytearray(256);fcntl.ioctl(f.fileno(),0xc1007c00,data,True)
   if bytes(data[16:48]).split(b'\0')[0].decode()=='SM8150 IPE':media.append(str(path))
  except OSError:continue
 assert len(media)==1
 case=root/'replay';case.mkdir()
 for name in ['full-private.bin','pd10-private.bin','parameters-private.bin']:shutil.copyfile(root/name,case/name)
 with (case/'client.log').open('xb') as log:
  child=subprocess.Popen([str(root/'tone-replay'),video[0],media[0],str(case)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('fixed-input-tone-replay',client_pid=child.pid);code=child.wait(timeout=45)
 text=(case/'client.log').read_text(errors='replace');state['replay_exit_code']=code
 assert code==0 and 'TONE_REPLAY_RESULT result=0 frames=5' in text,text[-3000:]
 rows=re.findall(r'REPLAY_FRAME mode=(\d+) flags=(\d+) full=([0-9a-f]+) pd10=([0-9a-f]+) output=([0-9a-f]+)',text)
 assert len(rows)==5 and len({r[2] for r in rows})==len({r[3] for r in rows})==1
 assert rows[0][-1]==rows[4][-1]
 state['replay_frames']=len(rows);state['stock_repeat_equal']=True
 idle();s=status();assert s['jobs']==s['completed']==s['direct_completed']==5 and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
