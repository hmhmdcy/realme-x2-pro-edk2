from pathlib import Path
import hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel197');p=k/'drivers/media/platform/qcom/camss/camss.c';s=p.read_text();old='''		if (mipi_csi2->clock_lane > 4)
			return -EINVAL;
''';new='''		/* Qualcomm 3-phase PHYs label the fixed D-PHY clock lane 7. */
		if (mipi_csi2->clock_lane > 4 && mipi_csi2->clock_lane != 7)
			return -EINVAL;
''';assert s.count(old)==1;backup=out/'camss-before-clock-fix-private.c';assert not backup.exists();backup.write_bytes(p.read_bytes());p.write_text(s.replace(old,new));r=dict(stage=197,old_source_sha256=hashlib.sha256(s.encode()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),qualcomm_clock_lane_7_restored=True,data_lane_bounds_and_duplicate_guards_preserved=True,cphy_guards_unchanged=True,source='https://android.googlesource.com/kernel/common/+/fb73974172ff/Documentation/devicetree/bindings/media/qcom%2Ccamss.txt');(ref/'camss-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
