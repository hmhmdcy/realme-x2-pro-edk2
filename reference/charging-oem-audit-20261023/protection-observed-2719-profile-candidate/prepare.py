"""Derive only offline source candidates from the installed7848 observer source."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'protection-query-observer-candidate'
PARSER=HERE.parent/'protection-evidence-parser-candidate/parse-evidence.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def replace(text,old,new):
    assert text.count(old)==1,(old,text.count(old));return text.replace(old,new)

def main():
    expected={'gauge-protocol.h':'98148c0701d000c21c7a9be60d0d14e412887f90fc1b83d0a3de8168359c28df',
      'gauge-i2c.h':'8846d20648dc0b137a2608be9a7ed479ecd692b17db6875a2a18a2d046d7c8b2',
      'samurai-gauge-protection.c':'3e1e81a341a5df072cde2c57ec7505096c192e7b873cfbb2720375ae7f9b8f6d'}
    original={name:(BASE/name).read_bytes() for name in expected}
    assert all(sha(raw)==expected[name] for name,raw in original.items())
    text=original['gauge-protocol.h'].decode()
    insert='''/* Explicit diagnostic profile, never inferred from a returned length byte.
 * DeviceType must come from this batch's complete validated0001 frame. */
enum sm_mac_diagnostic_profile {
	SM_MAC_PROFILE_STANDARD,
	SM_MAC_PROFILE_OBSERVED_2719_0056_3,
};

static inline int sm_mac_observe_profile_size(unsigned int command,
	unsigned int profile, unsigned int verified_device_type)
{
	if (profile == SM_MAC_PROFILE_STANDARD)
		return sm_mac_observe_data_size(command);
	if (profile != SM_MAC_PROFILE_OBSERVED_2719_0056_3) return -EINVAL;
	if (verified_device_type != 0x2719) return -ENODEV;
	return command == 0x0056 ? 3 : sm_mac_observe_data_size(command);
}

'''
    text=replace(text,'static inline int sm_mac_validate_sized(',insert+'static inline int sm_mac_validate_sized(')
    outputs={'gauge-protocol.h':text}
    text=original['gauge-i2c.h'].decode()
    insert='''/* Explicit profile is permitted only with this batch's validated identity. */
static inline int sm_gauge_mac_observe_profile_locked(struct i2c_client *g,
	unsigned int command, unsigned int profile, unsigned int verified_device_type,
	struct sm_mac_receipt *receipt)
{
	if (!receipt) return -EINVAL;
	*receipt = (struct sm_mac_receipt){ .command = command,
		.expected_size = sm_mac_observe_profile_size(command, profile,
						   verified_device_type) };
	return sm_gauge_mac_transfer_locked(g, command, receipt->raw,
					   receipt->expected_size, receipt);
}
'''
    text=replace(text,'#endif\n',insert+'#endif\n');outputs['gauge-i2c.h']=text
    text=original['samurai-gauge-protection.c'].decode()
    text=replace(text,'/* Fixed observation recipe, never a user-supplied MAC selector. */','''/* Opt-in at module load only; no runtime profile change or attempt reset. */
static bool observed_2719_diagnostic;
module_param(observed_2719_diagnostic, bool, 0444);
MODULE_PARM_DESC(observed_2719_diagnostic, "Diagnostic2719 profile:0056 payload3 only after validated0001");

/* Fixed observation recipe, never a user-supplied MAC selector. */''')
    text=replace(text,'\tbool attempted, terminal;','\tbool attempted, terminal, profile_identity_verified;\n\tunsigned int diagnostic_profile;')
    text=replace(text,'\t*e = (struct sm_mac_evidence){ .attempted = true };','''	*e = (struct sm_mac_evidence){ .attempted = true,
		.diagnostic_profile = observed_2719_diagnostic ?
			SM_MAC_PROFILE_OBSERVED_2719_0056_3 : SM_MAC_PROFILE_STANDARD };''')
    text=replace(text,'\tif (sm_le16(e->frames[0].raw + 2) != 0x2719) { ret = -ENODEV; goto out; }','''	if (sm_le16(e->frames[0].raw + 2) != 0x2719) { ret = -ENODEV; goto out; }
	e->profile_identity_verified = true;
	for (unsigned int i = 1; i < ARRAY_SIZE(sm_evidence_commands); i++)
		e->frames[i].expected_size = sm_mac_observe_profile_size(
			sm_evidence_commands[i], e->diagnostic_profile, 0x2719);''')
    text=replace(text,'\t\tret = sm_gauge_mac_observe_locked(p->gauge, sm_evidence_commands[i], &e->frames[i]);','''		ret = sm_gauge_mac_observe_profile_locked(p->gauge, sm_evidence_commands[i],
			e->diagnostic_profile, sm_le16(e->frames[0].raw + 2), &e->frames[i]);''')
    text=replace(text,'n = sysfs_emit(buf, "schema=1 attempted=%d terminal=%d stage=%u error=%d "','''n = sysfs_emit(buf, "schema=2 diagnostic_profile=%u profile_identity_verified=%d "
		"attempted=%d terminal=%d stage=%u error=%d "''')
    text=replace(text,'"compatibility_verified=0\\n", e->attempted, e->terminal, e->stage, e->error,','''"compatibility_verified=0\\n",
		e->attempted ? e->diagnostic_profile : (observed_2719_diagnostic ?
			SM_MAC_PROFILE_OBSERVED_2719_0056_3 : SM_MAC_PROFILE_STANDARD),
		e->profile_identity_verified, e->attempted, e->terminal, e->stage, e->error,''')
    outputs['samurai-gauge-protection.c']=text
    original_parser=PARSER.read_bytes();assert sha(original_parser)=='2ee04828775c330bfdafdca47e945645708f90e581c8939cd5932d6f8f1dc5b8'
    text=original_parser.decode()
    text=replace(text,'"""Parse saved mac_evidence text only. No device, transport or policy API."""','"""Explicit-profile schema2 saved diagnostic cache only; no transport or policy API."""')
    text=replace(text,'HEADER = frozenset(\'schema attempted',"PROFILES = {'standard': 0, 'observed-2719-0056-3': 1}\nHEADER = frozenset('schema diagnostic_profile profile_identity_verified attempted")
    text=replace(text,"FLAGS = frozenset('attempted terminal", "FLAGS = frozenset('profile_identity_verified attempted terminal")
    text=replace(text,'def parse_saved(data, decoder, decoder_sha256):','def parse_saved_profile(data, decoder, decoder_sha256, *, profile):\n    require(profile in PROFILES, \'explicit known diagnostic profile required\')')
    text=replace(text,"require(header['schema'] == 1 and header['compatibility_verified'] == 0, 'unsupported evidence schema')", "require(header['schema'] == 2 and header['diagnostic_profile'] == PROFILES[profile] and\n            header['compatibility_verified'] == 0, 'schema2/profile mismatch; never relabel legacy cache')\n    sizes = SIZES[:-1] + ((3 if PROFILES[profile] == 1 and header['profile_identity_verified'] else 4),)")
    text=replace(text,"if key != 'schema'", "if key not in ('schema', 'diagnostic_profile')")
    text=replace(text,'arguments = [str(decoder)]','arguments = [str(decoder), \'--profile\', profile]')
    text=replace(text,"frame['expected_size'] == (SIZES[i] if header['attempted'] else 0)","frame['expected_size'] == (sizes[i] if header['attempted'] else 0)")
    marker="    for key in ('before', 'after'):"
    text=replace(text,marker,"    identity = frames[0].get('decoded', {})\n    identity_verified = (identity.get('validate_rc') == 0 and identity.get('value') == 0x2719)\n    require(bool(header['profile_identity_verified']) == identity_verified, 'profile lacks this batch identity proof')\n"+marker)
    text=replace(text,"'schema': 'samurai-saved-mac-evidence-analysis-v1',", "'schema': 'samurai-explicit-profile-mac-analysis-v2', 'diagnostic_profile': profile,")
    text=replace(text,"    args = parser.parse_args()", "    parser.add_argument('--profile', choices=tuple(PROFILES), required=True)\n    args = parser.parse_args()")
    text=replace(text,'parse_saved(source.read_bytes(), args.decoder.resolve(), args.decoder_sha256)','parse_saved_profile(source.read_bytes(), args.decoder.resolve(), args.decoder_sha256, profile=args.profile)')
    outputs['parse-saved-profile.py']=text
    patches=[]
    for name,text in outputs.items():
        (HERE/name).write_text(text)
        old=original.get(name,original_parser).decode()
        old_name='parse-evidence.py' if name=='parse-saved-profile.py' else name
        patches.append(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='original/'+old_name,tofile='candidate/'+name)))
    (HERE/'profile.patch').write_text(''.join(patches))
    (HERE/'source-base.json').write_text(json.dumps({'observer_source_module_sha256':'7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044',
       'source_base':expected,'original_parser_sha256':sha(original_parser),'default_profile':'standard',
       'opt_in_module_parameter':'observed_2719_diagnostic=1','parameter_mode':'0444','cache_schema':2,
       'profiles':{'0':'standard','1':'observed-2719-0056-3'},'normal_health_or_six_command_policy_changed':False,
       'module_or_new_query_created':False},indent=2)+'\n')
    print(json.dumps({'offline_source_derived':True,'files':{name:sha((HERE/name).read_bytes()) for name in outputs}}))

if __name__=='__main__':main()
