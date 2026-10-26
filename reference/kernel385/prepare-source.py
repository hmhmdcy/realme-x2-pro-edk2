from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;name='camss-icp-a5-boot-test.c';before=(P/(name+'.before')).read_text();s=before
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
a=s.index('static const struct camss_a5_ipe_io test_io =');b=s.index('static char result[',a)
s=s[:a]+'''static struct camss_a5_ipe_io test_io;
static unsigned int test_width = 640, test_height = 480, test_port = 8;
static unsigned int test_cores = 1, test_frames = 1;
static bool test_uv_swap;
module_param(test_width, uint, 0400);
module_param(test_height, uint, 0400);
module_param(test_port, uint, 0400);
module_param(test_cores, uint, 0400);
module_param(test_frames, uint, 0400);
module_param(test_uv_swap, bool, 0400);
'''+s[b:]
replace('static char result[2048]','static char result[4096]')
replace('#define TEST_IMAGE_BYTES (640U * 480U * 3U / 2U)','#define TEST_IMAGE_MAX_BYTES (64U * 1024U * 1024U)\nstatic u32 test_image_bytes;')
a=s.index('static int test_frame(');b=s.index('static ssize_t image_read(',a);s=s[:a]+(HERE/'synthetic-frames.c').read_text()+'\n'+s[b:]
replace('.size = TEST_IMAGE_BYTES,','.size = TEST_IMAGE_MAX_BYTES,')
replace('\\\"output_crc\\\":%u}",','\\\"output_crc\\\":%u",')
replace('test_output_bytes, test_input_crc, test_output_crc);\n}', 'test_output_bytes, test_input_crc, test_output_crc);\n\tappend_frame_results();\n}')
replace('const struct firmware *firmware;\n\tint ret, stop;', 'const struct firmware *firmware;\n\tu32 sequence;\n\tint ret, stop;')
replace('\tfinished = false;\n\tdev_info(dev, "A5 diagnostic run begin after binding', '\tfinished = false;\n\ttest_frames_done = 0;\n\tmemset(frame_observations, 0, sizeof(frame_observations));\n\tdev_info(dev, "A5 diagnostic run begin after binding')
replace('''\t\tphase = "process-ipe-rt";
\t\tret = test_frame(a5);
\t\tif (ret)
\t\t\tgoto done;''','''\t\tfor (sequence = 0; sequence < test_frames; sequence++) {
\t\t\tphase = sequence & 1 ? "process-ipe-non-rt" : "process-ipe-rt";
\t\t\tret = test_frame(a5, sequence & 1 ? &session_non_rt : &session_rt,
\t\t\t\t\t sequence);
\t\t\tif (ret)
\t\t\t\tgoto done;
\t\t}''')
replace('''static int __init boot_test_init(void)
{
\tint ret;

\tret = bus_register_notifier''','''static int __init boot_test_init(void)
{
\tu32 stripe_bytes;
\tu64 image_bytes;
\tint ret;

\ttest_io.input = (struct camss_a5_nv12_layout) {
\t\ttest_width, test_height, test_width, test_height, test_uv_swap };
\ttest_io.output = test_io.input;
\ttest_io.output_port = test_port;
\tret = camss_a5_ipe_bypass_size(&test_io, test_cores, &stripe_bytes);
\tif (ret || !test_frames || test_frames > ARRAY_SIZE(frame_observations))
\t\treturn -EINVAL;
\timage_bytes = (u64)test_width * test_height * 3 / 2;
\tif (image_bytes > TEST_IMAGE_MAX_BYTES)
\t\treturn -E2BIG;
\ttest_image_bytes = image_bytes;
\tret = bus_register_notifier''')
(P/(name+'.proposed')).write_text(s);(HERE/name).write_text(s)
relative='drivers/media/platform/qcom/camss/'+name
(HERE/'diagnostic-frames.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=385,parent='5a0df37d3e9c8971d55186e468b38b424c8387dc',changed=[name],soc_transport_and_serializer_unchanged=True,parameterized_synthetic_frames=True,installed=False),indent=2)+'\n')
print('Prepared variable synthetic frames with alternating RT/non-RT handles and per-frame evidence.')
