# VBUS budget fence: independent static scope review

The reviewed WIP source snapshot has no confirmed new blocker in the normal DEVICE system-PM software-budget-work scope. The exact patch was independently reconstructed from the three candidate files against the pinned bd8a/9eec/525c baseline. This is not a final test or deployment approval.

Both enqueue sites are under the same DWC spinlock as the new gate. A worker that captured an old positive limit is joined after close releases that lock, before close requests zero. The actual paired provider releases its own mutex before reporting a power-supply change, and the budget worker does not call PM or join another work. Open clears the stored allowance, queues nothing, and a reported resume failure closes it again.

Close logs a failed zero request and still allows PM to return success. Do not equate that return with a proved zero publication; the normal success reasoning requires the paired provider-first ordering and the actual unpaused provider accepting zero. The inserted header field also changes subsequent struct offsets: all DWC header consumers must use the same rebuilt kernel. These are explicit integration/claim limits, not findings that the intended ordinary path currently fails.

[static-review.json](static-review.json) binds the exact source snapshot and line anchors. The author is still preparing fixtures and final delivery; none were executed or approved here. No devices, SDK, 284 storage helper, build, or Git operation was used. Runtime/direct_complete, UDC/DMA/resource teardown and the unchanged core's handling of gadget resume errors remain outside scope.
