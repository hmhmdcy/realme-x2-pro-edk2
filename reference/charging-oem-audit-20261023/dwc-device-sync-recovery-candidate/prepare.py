"""Independent gadget/header-only candidate from saved Image363 source."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'apsd-integration/current-r7/snapshots'
sha=lambda b:hashlib.sha256(b).hexdigest()
paths={name:BASE/('drivers--usb--dwc3--'+name) for name in ['gadget.c','core.h','core.c']}
link=json.loads((BASE.parent/'image-source-linkage.json').read_text())
for name,p in paths.items():
 item=next(x for x in link['comparisons'] if x['path']=='drivers/usb/dwc3/'+name)
 assert item['byte_equal_to_original_image_source'] and sha(p.read_bytes())==item['base_sha256'],name
def extract(source,name):
 m=re.search(r'^(?:static )?(?:int|void|irqreturn_t|bool)\s+'+name+r'\([^;]*?\)\s*\{',source,re.M)
 assert m,name
 start=m.start();pos=source.index('{',start);depth=0
 for token in re.finditer(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]',source[pos:],re.S):
  if token.group()=='{':depth+=1
  if token.group()=='}':
   depth-=1
   if not depth:return source[start:pos+token.end()]
 raise AssertionError(name)
original=paths['gadget.c'].read_text();gadget=original
old=extract(original,'dwc3_schedule_err_recovery')
new=old.replace('\tdwc->err_state = DWC3_ERR_RECOVERY;', '''	/* Called with dwc->lock held. Count every real IRQ error, including
	 * requests coalesced by schedule_work() into an already-pending work.
	 */
	dwc->err_event_seq++;
	dwc->err_state = DWC3_ERR_RECOVERY;''')
assert old!=new;gadget=gadget.replace(old,new)
old=extract(original,'dwc3_err_recovery_work')
new=r'''/* Stack-only receipt, not a controller terminal state or IRQ-depth owner. */
struct dwc3_recovery_result {
	const char *stage;
	u64 start_seq, end_seq;
	bool pending;
};

/* Caller holds connect_mutex; core/PHY are already powered. No PM get/put,
 * new retry loop or IRQ enable/disable is introduced by this helper.
 */
static int dwc3_gadget_recover_locked(struct dwc3 *dwc, bool claim,
				      struct dwc3_recovery_result *result)
{
	unsigned long flags;
	int ret = 0;

	lockdep_assert_held(&dwc->connect_mutex);
	spin_lock_irqsave(&dwc->lock, flags);
	result->start_seq = dwc->err_event_seq;
	result->end_seq = result->start_seq;
	result->pending = false;
	/* A synchronous resume failure cannot itself revive an old failure.
	 * A real IRQ still uses the original schedule_err_recovery policy.
	 */
	if (dwc->err_state == DWC3_ERR_UNRECOVERABLE) {
		result->stage = "existing-unrecoverable(policy-EIO)";
		spin_unlock_irqrestore(&dwc->lock, flags);
		return -EIO;
	}
	if (!claim && dwc->err_state != DWC3_ERR_RECOVERY) {
		result->stage = "stale-work";
		spin_unlock_irqrestore(&dwc->lock, flags);
		return 0;
	}
	dwc->err_state = DWC3_ERR_RECOVERY;
	spin_unlock_irqrestore(&dwc->lock, flags);

	result->stage = "disconnect";
	ret = dwc3_gadget_soft_disconnect(dwc);
	dwc3_disconnect_gadget_sleepable(dwc);
	if (ret)
		goto publish;

	result->stage = "disconnect-only";
	if (dwc->softconnect) {
		u32 count;

		/* Join the existing IRQ handler before resetting its event buffer.
		 * This does not re-enable a pending runtime-suspend IRQ or prove
		 * that a latched event was consumed.
		 */
		synchronize_irq(dwc->irq_gadget);
		spin_lock_irqsave(&dwc->lock, flags);
		count = ++dwc->err_recovery_count;
		spin_unlock_irqrestore(&dwc->lock, flags);
		if (count > DWC3_ERR_RECOVERY_MAX) {
			result->stage = "count-limit(policy-EIO)";
			ret = -EIO;
			goto publish;
		}
		result->stage = "connect";
		ret = dwc3_gadget_soft_connect(dwc);
		if (!ret)
			result->stage = "connect-complete";
	}

publish:
	/* IRQ arrival and publication linearize on the existing spinlock.
	 * Never erase a real error delivered after this attempt's snapshot,
	 * including when this attempt itself failed. No new event => retain
	 * the original success/failure policy and existing count semantics.
	 */
	spin_lock_irqsave(&dwc->lock, flags);
	result->end_seq = dwc->err_event_seq;
	result->pending = result->end_seq != result->start_seq;
	if (result->pending)
		dwc->err_state = DWC3_ERR_RECOVERY;
	else
		dwc->err_state = ret ? DWC3_ERR_UNRECOVERABLE : DWC3_ERR_NONE;
	spin_unlock_irqrestore(&dwc->lock, flags);
	/* The IRQ already requested work; explicitly preserve an execution
	 * opportunity even when its request coalesced with a running worker.
	 * One call only: no synchronous second recovery or new retry loop.
	 */
	if (result->pending)
		schedule_work(&dwc->err_recovery_work);
	return ret;
}

static void dwc3_err_recovery_work(struct work_struct *work)
{
	struct dwc3 *dwc = container_of(work, struct dwc3, err_recovery_work);
	struct dwc3_recovery_result result;
	int ret;

	mutex_lock(&dwc->connect_mutex);
	ret = dwc3_gadget_recover_locked(dwc, false, &result);
	mutex_unlock(&dwc->connect_mutex);
	if (ret || result.pending)
		dev_err(dwc->dev,
			"controller recovery stage=%s error=%d seq=%llu->%llu pending_at_publish=%u\n",
			result.stage, ret, (unsigned long long)result.start_seq,
			(unsigned long long)result.end_seq, result.pending);
}'''
gadget=gadget.replace(old,new)
old=extract(original,'dwc3_gadget_resume')
new=r'''int dwc3_gadget_resume(struct dwc3 *dwc)
{
	struct dwc3_recovery_result result;
	int primary, recovery;

	if (!dwc->gadget_driver || !dwc->softconnect)
		return 0;
	/* HOST is not a gadget caller; keep OTG's original connect behavior. */
	if (dwc->current_dr_role != DWC3_GCTL_PRTCAP_DEVICE)
		return dwc3_gadget_soft_connect(dwc);

	mutex_lock(&dwc->connect_mutex);
	/* Preserve the original first attempt, even with an old error state.
	 * Only the new synchronous recovery claim refuses to revive it.
	 */
	primary = dwc3_gadget_soft_connect(dwc);
	if (primary) {
		recovery = dwc3_gadget_recover_locked(dwc, true, &result);
		dev_err(dwc->dev,
			"DEVICE resume primary=%d recovery=%d stage=%s seq=%llu->%llu pending_at_publish=%u\n",
			primary, recovery, result.stage,
			(unsigned long long)result.start_seq,
			(unsigned long long)result.end_seq, result.pending);
	}
	mutex_unlock(&dwc->connect_mutex);
	/* Existing core PM common ignores this gadget errno and retains its
	 * powered success policy, SUSPHY and runtime pending-event tail.
	 */
	return primary;
}'''
gadget=gadget.replace(old,new)
header=paths['core.h'].read_text()
assert header.count('\tu32\t\t\terr_recovery_count;')==1
header=header.replace('\tu32\t\t\terr_recovery_count;', '\tu32\t\t\terr_recovery_count;\n\t/* Real IRQ error generations; protected by lock, not a retry count. */\n\tu64\t\t\terr_event_seq;')
header=header.replace(' * @err_recovery_count: number of consecutive error recovery attempts until',
 ' * @err_event_seq: real IRQ error generations, serialized by lock\n * @err_recovery_count: number of consecutive error recovery attempts until')
for name,newtext in [('gadget.c',gadget),('core.h',header)]:
 (HERE/name).write_text(newtext)
 (HERE/('baseline-'+name)).write_bytes(paths[name].read_bytes())
patch=''
for name in ['gadget.c','core.h']:
 patch+=''.join(difflib.unified_diff(paths[name].read_text().splitlines(True),(HERE/name).read_text().splitlines(True),fromfile='a/drivers/usb/dwc3/'+name,tofile='b/drivers/usb/dwc3/'+name))
(HERE/'sync-recovery.patch').write_text(patch)
r=dict(source_commit='ba61a62293e0f6bc5838c06f2e85e033e3d702a8',
 original={name:dict(path=str(p),sha256=sha(p.read_bytes())) for name,p in paths.items()},
 candidate={name:sha((HERE/name).read_bytes()) for name in ['gadget.c','core.h']},
 original_core_untouched=True,private_new_u64_fields=1,depends_on_R2=False,stopped_WIP_used=False,
 old_126_rerun=False,old_caller_review_reused=True,phone_accessed=False,sdk_invoked=False)
(HERE/'source-result.json').write_text(json.dumps(r,indent=2)+'\n')
print('generated independent gadget/header-only candidate')
