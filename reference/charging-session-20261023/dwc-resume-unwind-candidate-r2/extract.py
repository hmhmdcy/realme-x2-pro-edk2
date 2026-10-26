"""Extract fixed actual functions and rejected diagnostic variants; no kernel edit."""
from pathlib import Path
import hashlib, json, re
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
CORE = REF / 'charging-ui-audit-20261023/dwc-pm-error-unwind-candidate/core.c'
GADGET = REF / 'charging-ui-audit-20261023/dwc-suspend-halt-error-candidate/gadget.c'
HEADER = REF / 'charging-session-20261023/dwc-device-start-recovery-candidate/core.h'
OLD = REF / 'charging-session-20261023/dwc-resume-error-independent-review'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def function(text, name):
    match = re.search(r'^(?:static\s+)?(?:int|void|bool|irqreturn_t)\s+' + name + r'\([^;]*?\)\s*\{', text, re.M)
    assert match is not None, name
    pos = text.index('{', match.start()); end = pos + 1; depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[match.start():end]


def main():
    inputs = {CORE: '5331ae946cde894e2da484df5b8fbc6d386d117a60ad0e3dac5a1ebaaec6a17f',
              GADGET: 'aabfc928ca916d5b40492996153a03c08b837dcbb1d0c07091f23a35c2debfe2',
              HEADER: '9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'}
    for path, digest in inputs.items(): assert sha(path.read_bytes()) == digest
    core, gadget = CORE.read_text(), GADGET.read_text()
    names = [('dwc3_event_buffers_setup', core), ('dwc3_event_buffers_cleanup', core),
        ('dwc3_core_exit', core), ('dwc3_core_init_for_resume', core),
        ('dwc3_gadget_run_stop', gadget), ('dwc3_gadget_disable_irq', gadget), ('__dwc3_gadget_stop', gadget),
        ('dwc3_gadget_soft_disconnect', gadget), ('dwc3_gadget_soft_connect', gadget),
        ('dwc3_schedule_err_recovery', gadget), ('dwc3_gadget_recover_locked', gadget),
        ('dwc3_err_recovery_work', gadget), ('dwc3_gadget_resume', gadget), ('dwc3_check_event_buf', gadget),
        ('dwc3_resume_common', core), ('dwc3_runtime_resume', core), ('dwc3_pm_resume', core)]
    struct_start = gadget.index('struct dwc3_recovery_result {')
    result_struct = gadget[struct_start:gadget.index('};', struct_start) + 2]
    bodies = {name: function(text, name) for name, text in names}
    (HERE / 'actual-functions.inc').write_text(result_struct + '\n\n' + '\n\n'.join(bodies.values()) + '\n', newline='\n')
    # Diagnostic controls only. They are NOT kernel candidates/patches and are
    # never copied to a kernel tree. Exact old callers are otherwise retained.
    ignored = '\t\tdwc3_gadget_resume(dwc);\n\t\tbreak;'
    assert bodies['dwc3_resume_common'].count(ignored) == 1
    variants = []
    for label, cleanup in [('rejected_return', ''), ('rejected_exit', '\n\t\t\tsynchronize_irq(dwc->irq_gadget);\n\t\t\tdwc3_core_exit(dwc);')]:
        changed = bodies['dwc3_resume_common'].replace(ignored,
            '\t\tret = dwc3_gadget_resume(dwc);\n\t\tif (ret) {' + cleanup + '\n\t\t\treturn ret;\n\t\t}\n\t\tbreak;')
        changed = changed.replace('dwc3_resume_common(', label + '_resume_common(', 1)
        variants.append(changed)
        for caller in ('dwc3_runtime_resume', 'dwc3_pm_resume'):
            variants.append(bodies[caller].replace(caller + '(', label + '_' + caller + '(', 1)
                            .replace('dwc3_resume_common(', label + '_resume_common('))
    (HERE / 'rejected-diagnostic-functions.inc').write_text('\n\n'.join(variants) + '\n', newline='\n')
    evidence = {}
    for text, source, extra in [(core, CORE, ['dwc3_core_init', 'dwc3_core_remove', 'dwc3_free_event_buffers', 'dwc3_suspend_common']),
                                (gadget, GADGET, ['dwc3_gadget_start', 'dwc3_gadget_stop', 'dwc3_gadget_exit', 'dwc3_thread_interrupt', 'dwc3_process_event_buf'])]:
        for name in [n for n, src in names if src == text] + extra:
            body = function(text, name)
            evidence[name] = dict(source=source.relative_to(REF).as_posix(), line=text[:text.index(body)].count('\n') + 1, sha256=sha(body.encode()))
    manifest = json.loads((OLD / 'source-manifest.json').read_bytes())
    for item in manifest['files']: assert sha((OLD / item['snapshot']).read_bytes()) == item['sha256']
    result = dict(inputs={p.relative_to(REF).as_posix(): digest for p, digest in inputs.items()},
        extracted_actual_functions=len(bodies), function_evidence=evidence,
        pm_and_glue_source_manifest_sha256=sha((OLD / 'source-manifest.json').read_bytes()),
        rejected_variants_are_test_only=True, deployable_patch_generated=False,
        actual_sha256=sha((HERE / 'actual-functions.inc').read_bytes()),
        rejected_diagnostic_sha256=sha((HERE / 'rejected-diagnostic-functions.inc').read_bytes()))
    (HERE / 'source-result.json').write_text(json.dumps(result, indent=2) + '\n', newline='\n')
    print(json.dumps(dict(extracted=len(bodies), source_inputs_unchanged=True, deployable_patch_generated=False)))


if __name__ == '__main__': main()
