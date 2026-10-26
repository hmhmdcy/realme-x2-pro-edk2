from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel293')
report=dict(stage=293,actual_kernel_build=293,private_preview_reviewed=True,
 source_sha256=hashlib.sha256((private/'optical-11-private.nv12').read_bytes()).hexdigest(),
 recognizable_scene_edges_and_structures=True,dark_green_cast_remains=True,
 full_iq_calibration_complete=False,no_private_pixels_or_scene_description_in_public_receipt=True,
 white_balance_red_quarter_and_reopen_pattern_previews_reviewed=True)
(ROOT/'optical-review.json').write_text(json.dumps(report,indent=2)+'\n')
p=ROOT/'optical-pixel-validation.json';r=json.loads(p.read_text());assert r['frames'][1]['sha256']==report['source_sha256'];r.update(visual_review_pending=False,visual_review_evidence='optical-review.json');p.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(report,indent=2))
