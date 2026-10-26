"""Source-only default; no runtime request or device action."""
import json,sys
sys.dont_write_bytecode=True
import sources
sources.source_check()
print(json.dumps(dict(source_only=True,runtime_request_created=False,device_accessed=False)))
