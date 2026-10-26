from pathlib import Path
import hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel197');p=k/'drivers/media/platform/qcom/camss/camss-csid-gen2.c';s=p.read_text();old='''		dev_err(csid->camss->dev, "CSID reset timeout\\n");''';new='''		dev_err(csid->camss->dev,
			"CSID%u reset timeout: version=%#x irq=%#x mask=%#x strobe=%#x\\n",
			csid->id, readl(csid->base + CSID_HW_VERSION),
			readl(csid->base + CSID_TOP_IRQ_STATUS),
			readl(csid->base + CSID_TOP_IRQ_MASK),
			readl(csid->base + CSID_RST_STROBES));''';assert s.count(old)==1;(out/'camss-csid-gen2-before-diagnostic-private.c').write_bytes(p.read_bytes());p.write_text(s.replace(old,new));r=dict(stage=197,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),only_timeout_diagnostic_reads_added=True,power_and_reset_writes_unchanged=True);(ref/'csid-diagnostic-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
