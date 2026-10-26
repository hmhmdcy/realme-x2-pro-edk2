"""One actual-function borrowed-remove counterexample; does not rerun suites."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
OUT=HERE/'late-remove-counterexample'
OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
review=json.loads((HERE/'result.json').read_text())
assert review['passed']
for name,digest in review['files'].items():
    assert sha(HERE/name)==digest
for name in ['candidate-functions.inc','nbcon-functions.inc']:
    (OUT/name).write_bytes((HERE/name).read_bytes())
fake=(HERE/'fake-eud-os.h').read_text()
fake=fake.replace('static void unregister_console(struct console *c) { assert(!port_depth); }',
    'static void (*review_unregister_hook)(void);\nstatic void unregister_console(struct console *c) { assert(!port_depth); if(review_unregister_hook)review_unregister_hook(); }')
(OUT/'fake-eud-os.h').write_text(fake)
fixture=(HERE/'test-review.c').read_text().split('int main(void){',1)[0]
fixture+=r'''
static pthread_t late_console_thread;
static void finish_console_during_unregister(void){
 /* unregister_console must wait for an already entered callback. Its
  * callback may finish after remove's earlier RX cancellation. */
 release_writer();pthread_join(late_console_thread,NULL);
}
int main(void){
 clear();reset_review();up.console_registered=true;
 registers[EUD_REG_INT_STATUS_1/sizeof(u32)]=EUD_INT_RX_PENDING;
 review_mod_hook=pause_here;
 assert(!pthread_create(&late_console_thread,NULL,review_legacy,NULL));wait_for(&review_paused);
 /* The console already evaluated the non-stopping/non-quiet condition,
  * but has not yet queued RX work. begin can gate and cancel existing work. */
 quiet();u64 cookie=r.cookie;assert(!up.rx_work.work.pending);
 review_unregister_hook=finish_console_during_unregister;
 eud_remove(&device);
 assert(!eud&&!device.dev.data&&up.window_state==EUD_COM_REMOVED&&eud_window_orphan==cookie);
 assert(up.rx_work.work.pending==1);
 puts("{\"reproduced\":true,\"borrowed_remove\":true,\"late_rx_pending_after_remove\":true,\"endpoint_removed\":true,\"queued_work_executed_after_free\":false}");
 return 0;
}
'''
(OUT/'test-late-remove.c').write_text(fixture)
flags=['-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function',
    '-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread']
compile_result=subprocess.run(['gcc',*flags,str(OUT/'test-late-remove.c'),'-o',str(OUT/'test-late-remove')],capture_output=True,text=True)
run=subprocess.run([str(OUT/'test-late-remove')],capture_output=True,text=True,timeout=15) if compile_result.returncode==0 else None
assert compile_result.returncode==0,compile_result.stderr
assert run.returncode==0 and not run.stderr,(run.returncode,run.stdout,run.stderr)
result=dict(case=json.loads(run.stdout),source_candidate_sha256=review['source_candidate_sha256'],
    source_patch_sha256=review['source_patch_sha256'],
    actual_candidate_functions_unmodified=True,
    fake_boundary='console preemption between condition and queue; unregister joins callback; real candidate begin/remove/RX gates',
    original_suites_rerun=False,other_five_review_groups_rerun=False,compile_returncode=0,runtime_returncode=0,
    files={n:sha(OUT/n) for n in ['test-late-remove.c','fake-eud-os.h','candidate-functions.inc','nbcon-functions.inc']},
    phone_accessed=False,ssh_executed=False,sdk_invoked=False,author_files_modified=False)
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
