"""Prepare a standard lens candidate; deployment and userspace lifetime work remain separate."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel')
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],text=True).strip()
assert git('status','--porcelain')=='' and git('rev-parse','HEAD')=='3184c56b7f206ab000ab79bc99eb83d35c3e1d65'
subprocess.run(['git','-C',str(W),'switch','-c','samurai-main-focus274'],check=True)
mapping={'lc898219xi.c':'drivers/media/i2c/lc898219xi.c','onnn,lc898219xi.yaml':'Documentation/devicetree/bindings/media/i2c/onnn,lc898219xi.yaml'}
for name,dest in mapping.items():assert not (W/dest).exists();shutil.copyfile(R/name,W/dest)
p=W/'drivers/media/i2c/Kconfig';text=p.read_text();anchor='config VIDEO_S5KGW1\n';assert text.count(anchor)==1
text=text.replace(anchor,'config VIDEO_LC898219XI\n\ttristate "ON Semiconductor LC898219XI lens controller"\n\tdepends on I2C && VIDEO_DEV && PM\n\tselect MEDIA_CONTROLLER\n\tselect VIDEO_V4L2_SUBDEV_API\n\thelp\n\t  This is a V4L2 lens driver for the ON Semiconductor LC898219XI\n\t  autofocus controller. It provides absolute focus position control.\n\n'+anchor);p.write_text(text)
p=W/'drivers/media/i2c/Makefile';text=p.read_text();text+='\nobj-$(CONFIG_VIDEO_LC898219XI) += lc898219xi.o\n';p.write_text(text)
p=W/'arch/arm64/boot/dts/qcom/s5kgw1-samurai.dtsi';text=p.read_text();assert text.count('\t\tafvdd-supply = <&cam_main_vaf>;')==1
text=text.replace('\t\tafvdd-supply = <&cam_main_vaf>;','\t\tlens-focus = <&cam_main_lens>;')
anchor='\tcam_main: camera@10 {';assert text.count(anchor)==1
text=text.replace(anchor,'\tcam_main_lens: lens@72 {\n\t\tcompatible = "onnn,lc898219xi";\n\t\treg = <0x72>;\n\t\tvdd-supply = <&cam_main_vaf>;\n\t};\n\n'+anchor);p.write_text(text)
out=dict(stage=274,base=git('rev-parse','HEAD'),branch=git('branch','--show-current'),lens_vaf_is_sole_board_consumer=True,source_sha256=hashlib.sha256((R/'lc898219xi.c').read_bytes()).hexdigest(),
 physical_oem_command_response_not_standard_driver_validation=True,uncommitted_candidate=True,not_deployed=True,libcamera_lens_open_lifetime_must_be_fixed_before_deployment=True)
(R/'lens-candidate-source-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
