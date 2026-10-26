"""Join one timer worker and its owned CPU helpers; never clear a charger fault."""
from pathlib import Path
import importlib.util,json,os,signal,subprocess,sys,time,traceback
HERE=Path(__file__).resolve().parent
shutdown_spec=importlib.util.spec_from_file_location('timer_supervisor_shutdown',HERE/'shutdown-observer.py')
shutdown=importlib.util.module_from_spec(shutdown_spec);shutdown_spec.loader.exec_module(shutdown)
now=lambda:time.clock_gettime(time.CLOCK_BOOTTIME)
CANCELLED=False
def cancel(signum,frame):
    global CANCELLED
    CANCELLED=True
def save(name,value):
    with (HERE/name).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
def main():
    assert sys.argv[1:]==['--execute']
    assert not (HERE/'supervisor-terminal.json').exists() and not (HERE/'worker-launch.json').exists()
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    began=now();reason=None;error=None;after=None;helpers={};shutdown_event=None
    cleanup_stage=None;cleanup_trace=None
    with (HERE/'worker.stdout').open('xb') as out,(HERE/'worker.stderr').open('xb') as err:
        child=subprocess.Popen([sys.executable,'-B',str(HERE/'worker.py'),'--execute'],
            stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,close_fds=True)
    info=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
    save('worker-launch.json',dict(pid=child.pid,startticks=int(info[19]),supervisor_pid=os.getpid(),
        deadline_boottime=began+37030,heartbeat_limit_seconds=90))
    try:
        while child.poll() is None:
            heartbeat=HERE/'heartbeat.json';age=now()-began
            if heartbeat.exists():
                value=json.loads(heartbeat.read_bytes());assert value['pid']==child.pid
                age=now()-value['boottime'];assert age>=0
            if age>90:reason='heartbeat_deadline'
            if now()-began>37030:reason='absolute_deadline'
            if CANCELLED or (HERE/'cancel').exists():reason='cancelled'
            shutdown_event=shutdown.pending_openrc_shutdown()
            if shutdown_event is not None:reason='system_shutdown'
            if reason:break
            time.sleep(5)
    except BaseException as exc:
        reason='supervisor_error';error=repr(exc)
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGTERM)
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        rc=child.wait()
        # Helpers self-exit on PDEATHSIG, stale control or CHG stop. Inspect
        # their original identities; never signal an orphan or a reused PID.
        rows=[];path=HERE/'cpu-load-launch.json'
        if path.exists():
            launch=json.loads(path.read_bytes());assert launch['parent']==child.pid
            rows=launch['parts']
        until=now()+35
        while True:
            helpers={}
            for row in rows:
                proc=Path('/proc',str(row['pid']),'stat')
                if not proc.exists():helpers[str(row['pid'])]='absent';continue
                fields=proc.read_text().rsplit(')',1)[1].split()
                helpers[str(row['pid'])]='original_absent_pid_reused' if int(fields[19])!=row['startticks'] else fields[0]
            if all(v in ['absent','original_absent_pid_reused','Z'] for v in helpers.values()) or now()>=until:break
            time.sleep(1)
        helpers_ended=all(v in ['absent','original_absent_pid_reused','Z'] for v in helpers.values())
        if shutdown_event is None:
            shutdown_event=shutdown.pending_openrc_shutdown()
            if shutdown_event is not None:reason='system_shutdown'
        if shutdown_event is None:
            spec=importlib.util.spec_from_file_location('timeout_worker_cleanup',HERE/'worker.py')
            w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);io=w.IO()
            try:
                io.setup();cleanup_stage='observe';after=io.observe()
                cleanup_stage='validate';io.validate(after)
                cleanup_stage='behaviour'
                assert after['behaviour']=='auto'
            except BaseException as exc:
                error=repr(exc);cleanup_trace=traceback.format_exc()
            finally:io.close()
        returncode=rc if error is None and helpers_ended else 1
        save('supervisor-terminal.json',dict(pid=os.getpid(),child_pid=child.pid,child_joined=True,
            child_returncode=rc,watchdog_reason=reason,cleanup_error=error,helpers=helpers,
            cleanup_stage=cleanup_stage,cleanup_trace=cleanup_trace,
            helpers_ended=helpers_ended,after=after,returncode=returncode,
            shutdown_event=shutdown_event,fresh_IO_skipped_for_shutdown=shutdown_event is not None,
            no_automatic_fault_clear=True,no_charging_parameter_or_mode_write=True))
    return returncode
if __name__=='__main__':raise SystemExit(main())
