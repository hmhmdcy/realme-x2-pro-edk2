from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';camss=source/'drivers/media/platform/qcom/camss'
base='07d2ca735f88649587c0e89802febff6dbf2b443';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True)
assert git('rev-parse','HEAD').strip()==base and not git('status','--porcelain')
subprocess.run(['git','-C',str(source),'switch','-c','samurai-ipe-coarse-io425'],capture_output=True,check=True)
names=['camss-icp-a5-boot.h','camss-icp-a5-boot.c','camss-icp-a5-ipe.c'];before={n:(camss/n).read_text() for n in names}
text=before[names[0]];needle='struct camss_a5_ipe_io {';assert text.count(needle)==1
text=text.replace(needle,'''/* Canonical native quarter-resolution PD10 backing, not generated pixels. */
struct camss_a5_pd10_layout {
	u32 width, height, stride, slice_height, bytes;
};
int camss_a5_ipe_pd10_quarter(const struct camss_a5_nv12_layout *full,
			    struct camss_a5_pd10_layout *result);

'''+needle)
needle='struct camss_a5_session {';assert text.count(needle)==1
text=text.replace(needle,'''/* Optional input-DS4 description only. The submitting path must additionally
 * own/populate backing, configure the session, and supply multipass geometry.
 * NULL coarse preserves the ordinary NV12/NV21 IO bytes. */
int camss_a5_ipe_encode_io(void *destination, u32 bytes,
			 const struct camss_a5_ipe_io *io,
			 const struct camss_a5_pd10_layout *coarse);

'''+needle);(camss/names[0]).write_text(text)
text=before[names[1]];a=text.index('static int encode_ipe_io(');b=text.index('static int region_packet_locked(',a)
text=text[:a]+(HERE/'coarse-io.c').read_text().split('*/',1)[1].lstrip()+'\n'+text[b:]
needle='ret = encode_ipe_io(a5->config.cpu, a5->config.bytes, io);';assert text.count(needle)==1
text=text.replace(needle,'ret = camss_a5_ipe_encode_io(a5->config.cpu, a5->config.bytes, io, NULL);');(camss/names[1]).write_text(text)
text=before[names[2]]+'\n'+(HERE/'pd10-layout.c').read_text().split('*/',1)[1].lstrip();(camss/names[2]).write_text(text)
patch='';rows=[]
for n in names:
 rel='drivers/media/platform/qcom/camss/'+n;after=(camss/n).read_text();patch+=''.join(difflib.unified_diff(before[n].splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel));rows.append(dict(path=rel,sha256=hashlib.sha256((camss/n).read_bytes()).hexdigest()))
(HERE/'coarse-io-layout.patch').write_text(patch)
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
subprocess.run(['git','-C',str(source),'add','--',*[str(camss/n) for n in names]],check=True)
subprocess.run(['git','-C',str(source),'commit','-m','media: camss: describe native PD10 quarter backing and optional IPE IO'],check=True)
r=dict(stage=425,parent_commit=base,commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),source_hashes=rows,
 ordinary_runtime_configuration_still_passes_null_coarse=True,coarse_runtime_submission_not_connected=True,pd10_pixel_producer_not_implemented=True,
 no_new_user_api=True,no_board_or_sensor_change=True,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
