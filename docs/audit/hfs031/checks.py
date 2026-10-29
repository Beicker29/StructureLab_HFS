"""Final audit checks; uses existing verified installations, creates new outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT=Path(__file__).resolve().parents[3]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verification',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    env.pop('PYTHONPATH',None)
    env.update(PYTHONNOUSERSITE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONUTF8='1')
    records=[]

    def run(label,command,cwd=ROOT):
        command=list(map(str,command))
        r=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
        record=dict(label=label,command=command,cwd=str(cwd),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
        (out/f'{label}.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        records.append(record)
        print(label,r.returncode,flush=True)
        assert r.returncode==0, label

    external=Path(tempfile.mkdtemp(prefix='h31-final-'))
    assert not external.is_relative_to(ROOT)
    (external/'tests/fixtures/hfs031').mkdir(parents=True)
    inputs=['tests/test_hfs031_de_audit.py','tests/fixtures/hfs031/oracles.json']
    for path in inputs:
        shutil.copyfile(ROOT/path,external/path)
        assert (external/path).read_bytes()==(ROOT/path).read_bytes()
    for mode in ['wheel','editable']:
        executable=json.loads((args.verification/f'imports-{mode}.json').read_text(encoding='utf-8'))['command'][0]
        run('suite-'+mode,[executable,'-m','pytest','-q','-rx','--tb=short','-p','no:cacheprovider',
            'tests/test_hfs031_de_audit.py',f'--junitxml={out/(mode+".xml")}',
            f'--basetemp={external/("tmp-"+mode)}'],external)
    run('ruff',[sys.executable,'-m','ruff','check','src','tests','scripts',
        'docs/audit/hfs031/oracles.py','docs/audit/hfs031/probe.py','docs/audit/hfs031/checks.py','--exclude','tests/.tmp_tests'])
    run('schemas',[sys.executable,'scripts/generate_hfs022_schemas.py','--check'])
    run('registry',[sys.executable,'scripts/audit_hfs023.py','--check'])
    run('oracle-reproduction',[sys.executable,'docs/audit/hfs031/oracles.py','--out',out/'oracles.json'])
    assert json.loads((out/'oracles.json').read_text())==json.loads((ROOT/inputs[1]).read_text())
    run('diff-check',['git','diff','--check'])
    run('protected-diff',['git','diff','--exit-code','HEAD','--','src','examples','schemas','data','pyproject.toml',
        'docs/contracts','docs/audit/hfs030','docs/audit/hfs000'])
    run('head',['git','rev-parse','HEAD'])
    run('status',['git','status','--short'])
    run('freeze',[sys.executable,'-m','pip','freeze','--all'])
    links=[]
    for path in (ROOT/'docs/audit/hfs031').glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            resolved=(path.parent/target.split('#')[0]).resolve()
            assert resolved.exists(), (path,target)
            links.append(dict(source=path.relative_to(ROOT).as_posix(),target=target))
    summary={'external_work':str(external),'no_production_sources_copied':True,
        'input_hashes':{p:hashlib.sha256((external/p).read_bytes()).hexdigest() for p in inputs},
        'checks':[{'label':r['label'],'returncode':r['returncode']} for r in records],
        'valid_document_links':links,'oracle_reproduction_exact':True}
    (out/'checks.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
