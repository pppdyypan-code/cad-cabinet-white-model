"""Optional real-Blender regression: python tests/integration.py --blender PATH."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/cad-cabinet-white-model'


def run(command, expected=0):
    result=subprocess.run(command,capture_output=True,text=True)
    if result.returncode!=expected:
        raise AssertionError(result.stdout+'\n'+result.stderr)
    return result.stdout


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='white-model-test-') as temp:
        out=Path(temp)
        project=out/'project.json'
        project.write_text((SKILL/'assets/example-project.json').read_text())
        cli=[sys.executable,str(SKILL/'scripts/workflow.py')]
        flags=['--project',str(project),'--blender',args.blender]
        run(cli+['build',*flags,'--out',str(out/'model')])
        source=out/'model/model.blend'
        run([args.blender,'-b','--factory-startup',str(source),'--python-exit-code','1',
             '-P',str(ROOT/'tests/blender_assertions.py')])
        # Reproduce an imported file whose current frame is bound to an old camera.
        binder=out/'bind.py'
        binder.write_text("import bpy\n"+
            "data=bpy.data.cameras.new('LegacyCamera')\n"+
            "cam=bpy.data.objects.new('LegacyCamera',data)\n"+
            "bpy.context.scene.collection.objects.link(cam)\n"+
            "m=bpy.context.scene.timeline_markers.new('LegacyShot',frame=1);m.camera=cam\n"+
            "bpy.ops.wm.save_as_mainfile(filepath="+repr(str(out/'bound.blend'))+")\n")
        run([args.blender,'-b','--factory-startup',str(source),'--python-exit-code','1','-P',str(binder)])
        source=out/'bound.blend'
        original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        command=cli+['preview',*flags,'--blend',str(source),'--out',str(out/'proofs'),
                     '--cameras','A','C','--size','320']
        run(command)
        result=json.loads((out/'proofs/preview-result.json').read_text())
        assert result['geometry_before']==result['geometry_after']
        assert len(result['cleared_camera_bindings'])==1
        assert len(result['renders'])==2
        assert result['renders'][0]['sha256']!=result['renders'][1]['sha256']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==original_hash
        assert json.loads(run(command).splitlines()[-1])['cached'] is True
        # A changed input must not reuse an old render or accept stale geometry.
        config=json.loads(project.read_text())
        config['cameras'][0]['position_mm'][2]=1200
        config['cameras'][0]['target_mm'][2]=1200
        project.write_text(json.dumps(config))
        assert json.loads(run(command).splitlines()[-1])['cached'] is False
        config['components'][0]['depth_mm']+=10
        project.write_text(json.dumps(config))
        assert 'Model parameters changed' in run(command,expected=1)
        config['components'][0]['depth_mm']-=10
        project.write_text(json.dumps(config))
        run(cli+['final',*flags,'--blend',str(source),'--out',str(out/'final')],expected=2)
        run(cli+['final',*flags,'--blend',str(source),'--out',str(out/'final'),
                 '--cameras','A','--size','320','--samples','8','--device','CPU'])
        final=json.loads((out/'final/final-result.json').read_text())
        assert [r['id'] for r in final['renders']]==['A']
        assert final['geometry_unchanged'] is True
        print(json.dumps({'ok':True,'checks':['dimensions','mesh reuse','miter',
            'timeline camera override','camera selection','source preservation',
            'geometry fingerprint','cache hit','camera cache invalidation',
            'stale model rejection','final selection required','selected final render']}))


if __name__=='__main__':
    main()
