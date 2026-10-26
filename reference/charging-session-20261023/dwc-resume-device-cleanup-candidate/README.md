# DO NOT EXECUTE — stopped, unreviewed WIP

This directory preserves an abandoned draft, not an approved or validated candidate. Do not apply its patch, run its generator as an update, compile it for deployment, or use it on a device. No tests or object build were run for these bytes. The root/R2 sources remain unchanged.

The draft generated three terminal-failure fields, IRQ parking and request/free serialization before the root review response arrived. Root stopped this direction because it expands default lifecycle behavior, poisons later binding/recovery rather than solving automatic recovery, and assumes IRQ disable-depth release after free without verifying actual IRQ-core teardown semantics. Fake counters cannot establish that behavior. These unresolved issues make the draft unsuitable for use.

The actual error-propagation gap and new caller evidence are retained in `../dwc-resume-error-independent-review/`. That review remains changes-required. The draft files are retained solely as rejected design history; no automatic consumer, build, phone, SSH, USB, SDK or shared-source mutation occurred.
