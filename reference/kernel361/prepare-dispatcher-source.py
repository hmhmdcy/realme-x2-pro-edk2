"""Fix notifier lifetime in the common dispatcher without changing its ABI."""
from pathlib import Path
import difflib,hashlib,json,shutil
import storage
HERE=Path(__file__).resolve().parent;old=storage.previous.candidate();new=old.parent/'libcamera361-event-dispatch-built';assert not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
name='src/libcamera/base/event_dispatcher_poll.cpp';p=new/'src/libcamera-v0.7.2'/name;before=p.read_text();s=before
a='\tprocessingEvents_ = true;\n\n\tfor (const pollfd &pfd : pollfds) {'
b='''	/* Synchronous IPC can dispatch events recursively from a notifier.
	 * Keep every map entry alive until the outermost dispatch has finished:
	 * an outer poll snapshot and callback may still refer to those entries.
	 */
	const bool wasProcessingEvents = processingEvents_;
	processingEvents_ = true;

	for (const pollfd &pfd : pollfds) {'''
assert s.count(a)==1;s=s.replace(a,b)
a='''		/* Erase the notifiers_ entry if it is now empty. */
		if (!set.notifiers[0] && !set.notifiers[1] && !set.notifiers[2])
			notifiers_.erase(iter);
	}

	processingEvents_ = false;'''
b='''	}

	processingEvents_ = wasProcessingEvents;
	if (processingEvents_)
		return;

	for (auto iter = notifiers_.begin(); iter != notifiers_.end();) {
		const EventNotifierSetPoll &set = iter->second;
		if (!set.notifiers[0] && !set.notifiers[1] && !set.notifiers[2])
			iter = notifiers_.erase(iter);
		else
			++iter;
	}'''
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
(HERE/'event-dispatcher-reentrancy.patch').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),s.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name)))
(HERE/'dispatcher-after.cpp').write_text(s)
(HERE/'dispatcher-source-state.json').write_text(json.dumps(dict(stage=361,source=str(new/'src/libcamera-v0.7.2'),baseline=str(old/'src/libcamera-v0.7.2'),file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    api_and_class_layout_unchanged=True,notifier_assertion_preserved=True,common_layer_fix=True,installed=False),indent=2)+'\n')
print('Prepared common dispatcher candidate: preserve outer processing state and defer all empty-entry erasure until outermost exit.')
