"""Keep generic sensor support and board wiring as separate local commits."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel');G=['git','-C',str(W)]
assert subprocess.check_output(G+['branch','--show-current'],text=True).strip()=='samurai-multicamera270'
assert subprocess.check_output(G+['rev-parse','HEAD'],text=True).strip()==json.loads((R/'telephoto-source-validation.json').read_text())['base_commit']
assert hashlib.sha256((W/'drivers/media/i2c/s5k3m5.c').read_bytes()).hexdigest()==json.loads((R/'current-module-build-validation.json').read_text())['source_sha256']
subprocess.run(G+['diff','--check'],check=True,capture_output=True)
sensor=['drivers/media/i2c/s5k3m5.c','drivers/media/i2c/s5k3m5-19mhz-tables.h','Documentation/devicetree/bindings/media/i2c/samsung,s5k3m5.yaml']
board=['arch/arm64/boot/dts/qcom/s5k3m5-samurai.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
subprocess.run(G+['add','--',*sensor],check=True)
subprocess.run(G+['commit','-m','media: i2c: support S5K3M5 19.2 MHz operation with standard supplies'],capture_output=True,check=True)
sensor_commit=subprocess.check_output(G+['rev-parse','HEAD'],text=True).strip()
subprocess.run(G+['add','--',*board],check=True)
subprocess.run(G+['commit','-m','arm64: dts: qcom: describe RMX1931 S5K3M5 telephoto camera'],capture_output=True,check=True)
board_commit=subprocess.check_output(G+['rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(G+['status','--porcelain'],text=True).strip()
report=dict(stage=270,branch='samurai-multicamera270',sensor_commit=sensor_commit,board_commit=board_commit,
 clean_source=True,original_maintained_branch_unchanged=True,not_pushed=True)
(R/'kernel-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
