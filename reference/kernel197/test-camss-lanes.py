from pathlib import Path
import hashlib,json,re,subprocess
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel197');source=Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/media/platform/qcom/camss/camss.c')
def function(s):
 i=s.index('static int camss_parse_endpoint_node(');a=s.index('{',i);j=a+1;depth=1
 while depth:depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[i:j]
oldtest=(ref.parent/'kernel124/test-cphy-contracts.py').read_text();prefix=oldtest.split("prefix='''",1)[1].split("'''",1)[0];fixture=oldtest.split("parser='''",1)[1].split("'''+func",1)[0]
body=r'''
static unsigned int cases;
static int parse(int expected) {
 struct camss_async_subdev csd={0};struct device dev={0};struct fwnode_handle ep={0};
 int r=camss_parse_endpoint_node(&dev,&ep,&csd);cases++;assert(r==expected);
 if(!r){assert(csd.interface.csiphy_id==fixture.base.port);assert(csd.interface.csi2.lane_cfg.num_data==fixture.bus.mipi_csi2.num_data_lanes);for(int i=0;i<csd.interface.csi2.lane_cfg.num_data;i++)assert(csd.interface.csi2.lane_cfg.data[i].pos==fixture.bus.mipi_csi2.data_lanes[i]);}
 free(csd.interface.csi2.lane_cfg.data);return r;
}
int main(void){
 fixture.bus_type=4;fixture.base.port=2;fixture.bus.mipi_csi2.clock_lane=7;fixture.bus.mipi_csi2.num_data_lanes=4;for(int i=0;i<4;i++)fixture.bus.mipi_csi2.data_lanes[i]=i;
 parse(0); /* Real SM8150 front endpoint: legacy clock 7, physical data 0..3. */
 for(int n=1;n<=4;n++){fixture.bus.mipi_csi2.num_data_lanes=n;parse(0);}fixture.bus.mipi_csi2.num_data_lanes=4;
 fixture.bus.mipi_csi2.data_lanes[3]=2;parse(-EINVAL);fixture.bus.mipi_csi2.data_lanes[3]=5;parse(-EINVAL);fixture.bus.mipi_csi2.data_lanes[3]=3;
 for(int c=5;c<=8;c++){if(c==7)continue;fixture.bus.mipi_csi2.clock_lane=c;parse(-EINVAL);}
 fixture.bus.mipi_csi2.clock_lane=0;for(int i=0;i<4;i++)fixture.bus.mipi_csi2.data_lanes[i]=i+1;parse(0);fixture.bus.mipi_csi2.data_lanes[0]=0;parse(-EINVAL);fixture.bus.mipi_csi2.data_lanes[0]=1;
 fixture.bus.mipi_csi2.num_data_lanes=0;parse(-EINVAL);fixture.bus.mipi_csi2.num_data_lanes=5;parse(-EINVAL);fixture.bus.mipi_csi2.num_data_lanes=4;
 parse_fail=-EIO;parse(-EIO);parse_fail=0;alloc_fail=1;parse(-ENOMEM);alloc_fail=0;
 fixture.bus_type=99;parse(-EINVAL);fixture.bus_type=1;for(int i=0;i<3;i++)fixture.bus.mipi_csi2.data_lanes[i]=i;
 for(int n=1;n<=3;n++){fixture.bus.mipi_csi2.num_data_lanes=n;parse(0);}fixture.bus.mipi_csi2.num_data_lanes=4;parse(-EINVAL);fixture.bus.mipi_csi2.num_data_lanes=3;
 fixture.bus.mipi_csi2.data_lanes[2]=1;parse(-EINVAL);fixture.bus.mipi_csi2.data_lanes[2]=3;parse(-EINVAL);fixture.bus.mipi_csi2.data_lanes[2]=2;
 for(int i=1;i<=5;i++){fixture.bus.mipi_csi2.line_orders[0]=i;parse(-EINVAL);}fixture.bus.mipi_csi2.line_orders[0]=0;
 fixture.bus.mipi_csi2.lane_polarities[1]=1;parse(-EINVAL);fixture.bus.mipi_csi2.lane_polarities[1]=0;
 printf("CAMSS_LANE_REGRESSION_PASS cases=%u\n",cases);return 0;
}
'''
results=[]
for label,driver in [('old',out/'camss-before-clock-fix-private.c'),('fixed',source)]:
 c=out/('lane-test-'+label+'-private.c');c.write_text(prefix+fixture+function(driver.read_text())+body);exe=out/('lane-test-'+label+'-private');p=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-Wno-missing-field-initializers','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(c),'-o',str(exe)],capture_output=True);(out/('lane-test-'+label+'-compile-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode();p=subprocess.run([str(exe)],capture_output=True,timeout=10);(out/('lane-test-'+label+'-run-private.log')).write_bytes(p.stdout+p.stderr);assert (p.returncode==0)==(label=='fixed');results.append(dict(label=label,returncode=p.returncode,source_sha256=hashlib.sha256(driver.read_bytes()).hexdigest()))
r=dict(stage=197,actual_parser_body_extracted=True,asan_ubsan_passed=True,cases=int(re.search(rb"cases=(\d+)",p.stdout).group(1)),old_source_fails_real_clock_7_endpoint=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),results=results);(ref/'camss-lane-host-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

