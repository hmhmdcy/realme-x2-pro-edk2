from pathlib import Path
import importlib.util,json,runpy,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';path=source/'drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
state=json.loads((HERE/'source-state.json').read_text());assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
old=path.read_bytes();assert old==(P/'camss-icp-a5-boot.c.proposed').read_bytes();(P/'camss-icp-a5-boot.c.before-irq-refinement').write_bytes(old)
runpy.run_path(str(HERE/'prepare-proposal.py'),run_name='__main__')
subprocess.run(['python3',str(HERE/'check-session.py')],check=True)
# Reject both old error-clobber interleavings using the same actual body model.
work=P/'session-regression';current=(work/'body.inc').read_text();text=old.decode();parts=['\n'.join(l for l in text.splitlines() if l.startswith('#define '))]
for start,end in [('static void command_failure(','static irqreturn_t a5_interrupt('),('static void process_message(','static irqreturn_t a5_interrupt_thread('),('static int send_packet(','bool camss_a5_backing_owned('),('static int quiesce_locked(','int camss_a5_stop(')]:
 a=text.index(start);b=text.index(end,a);parts.append(text[a:b])
try:
 (work/'body.inc').write_text('\n'.join(parts));q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe-before')],capture_output=True);assert not q.returncode,q.stderr.decode()
 for case in [25,26]:
  q=subprocess.run([str(work/'probe-before'),str(case)],capture_output=True,timeout=10);(work/(str(case)+'-before-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode
finally:(work/'body.inc').write_text(current)
path.write_bytes((P/'camss-icp-a5-boot.c.proposed').read_bytes());subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',str(path.relative_to(source))],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: retain command errors across successful and joining IRQ replies'],check=True,capture_output=True)
state.update(initial_commit=state['commit'],commit=git('rev-parse','HEAD'),irq_error_interleaving_negative_controls_rejected=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
