from pathlib import Path
import ctypes, json, os, re, subprocess, time, wave

os.umask(0o077)
out=Path('/var/lib/samurai/k175-stop');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k175-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#175 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
def cmd(args):
    p=subprocess.run(args,capture_output=True);assert p.returncode==0,(args,p.stderr.decode())
    return p.stdout.decode()
def pulse(args): return cmd(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+args])
def status(): return Path('/proc/asound/card0/pcm1c/sub0/status').read_text()
before=cmd(['dmesg']);(out/'dmesg-before-private.txt').write_text(before)
saved=cmd(['amixer','-c','0','contents']);(out/'mixer-before-private.txt').write_text(saved)
cases=[]
try:
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 1')
    time.sleep(.5)
    assert status().strip()=='closed'
    for index,rate in enumerate([48000,16000,32000,48000,48000,32000,16000,48000]):
        target=out/('capture-%d-private.wav'%index)
        with (out/('capture-%d-private.log'%index)).open('wb') as log:
            rec=subprocess.Popen(['arecord','-q','-D','hw:0,1','-r',str(rate),'-c','1','-f','S16_LE','-d','1',str(target)],stdout=log,stderr=log)
            try:
                time.sleep(.25);assert 'RUNNING' in status()
                assert rec.wait(timeout=4)==0
            finally:
                if rec.poll() is None:rec.terminate();rec.wait(timeout=3)
        with wave.open(str(target),'rb') as w: assert w.getnframes()==rate and w.getframerate()==rate
        assert status().strip()=='closed'
        cases.append(dict(case=index,rate=rate,capture_frames=rate,running_seen=True,closed_after_stop=True))
        time.sleep(.25)
    # Exercise real ALSA pause without closing or repowering the DAPM path.
    lib=ctypes.CDLL('libasound.so.2')
    ptr=ctypes.c_void_p
    signatures={'snd_pcm_open':([ctypes.POINTER(ptr),ctypes.c_char_p,ctypes.c_int,ctypes.c_int],ctypes.c_int),
      'snd_pcm_set_params':([ptr,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint],ctypes.c_int),
      'snd_pcm_start':([ptr],ctypes.c_int),'snd_pcm_pause':([ptr,ctypes.c_int],ctypes.c_int),
      'snd_pcm_readi':([ptr,ptr,ctypes.c_ulong],ctypes.c_long),'snd_pcm_drop':([ptr],ctypes.c_int),'snd_pcm_close':([ptr],ctypes.c_int),
      'snd_pcm_hw_params_malloc':([ctypes.POINTER(ptr)],ctypes.c_int),'snd_pcm_hw_params_current':([ptr,ptr],ctypes.c_int),
      'snd_pcm_hw_params_can_pause':([ptr],ctypes.c_int),'snd_pcm_hw_params_free':([ptr],None)}
    for name,(args,result) in signatures.items():getattr(lib,name).argtypes=args;getattr(lib,name).restype=result
    pcm=ptr();params=ptr();paused=False;pause_cycles=[]
    assert lib.snd_pcm_open(ctypes.byref(pcm),b'hw:0,1',1,0)==0
    try:
        assert lib.snd_pcm_set_params(pcm,2,3,1,48000,0,500000)==0
        assert lib.snd_pcm_hw_params_malloc(ctypes.byref(params))==0
        assert lib.snd_pcm_hw_params_current(pcm,params)==0
        pause_supported=bool(lib.snd_pcm_hw_params_can_pause(params))
        if pause_supported:
            assert lib.snd_pcm_start(pcm)==0
            samples=(ctypes.c_int16*4096)()
            for index in range(3):
                assert lib.snd_pcm_readi(pcm,samples,4096)==4096
                assert lib.snd_pcm_pause(pcm,1)==0;paused=True
                assert 'PAUSED' in status();time.sleep(.1)
                assert lib.snd_pcm_pause(pcm,0)==0;paused=False
                assert 'RUNNING' in status()
                assert lib.snd_pcm_readi(pcm,samples,4096)==4096
                pause_cycles.append(dict(cycle=index,paused_and_running_seen=True,frames_before_and_after=4096))
            assert lib.snd_pcm_drop(pcm)==0
    finally:
        if paused:lib.snd_pcm_pause(pcm,0)
        if params:lib.snd_pcm_hw_params_free(params)
        assert lib.snd_pcm_close(pcm)==0
finally:
    pulse('pactl suspend-source alsa_input.platform-sound.HiFi__Mic__source 0')
    time.sleep(3)
after=cmd(['dmesg']);(out/'dmesg-after-private.txt').write_text(after)
assert cmd(['amixer','-c','0','contents'])==saved
patterns={'warnings':'WARNING:','kernel_oops':'Oops:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out','resume_failed':'NGD resume failed','underflow':'underflow error','overflow':'overflow error','port_closed':'Port Closed'}
delta={n:after.count(p)-before.count(p) for n,p in patterns.items()};assert not any(delta.values()),delta
new=after[len(before):]
triggers=[dict(dai=int(a),command=int(b),channels=int(c),rate=int(d),result=int(e)) for a,b,c,d,e in re.findall(r'slim trigger dai=(\d+) command=(\d+) channels=(\d+) rate=(\d+) ret=(-?\d+)',new)]
assert all(t['result']==0 for t in triggers)
amps={a:Path('/sys/bus/i2c/devices/'+a+'/status').read_text().strip() for a in ['1-0039','1-003a']}
assert all('powered=0 muted=1' in v and 'failed=0' in v for v in amps.values())
report=dict(stage=175,kernel_build=175,cases=cases,real_pcm_pause_supported=pause_supported,pause_cycles=pause_cycles,
 trigger_events=triggers,fault_delta=delta,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 pcm_closed=status().strip()=='closed',amps=amps,mixer_unchanged=True,same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes())
assert report['taint']==0 and report['pcm_closed'] and report['same_boot']
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
