"""Record Git/AST preservation for HFS-015; does not validate AISC formulas."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from audit_baseline import write_json


class ResultTransport(ast.NodeTransformer):
    """Ignore only declared result transport, leaving capacity formulas/traces."""
    def visit_FunctionDef(self,node):
        if node.name in {"_result","_build_result","_build_flexure_result","check"}:
            node.body=[stmt for stmt in node.body if not (isinstance(stmt,ast.Assign)
                and len(stmt.targets)==1 and isinstance(stmt.targets[0],ast.Name)
                and stmt.targets[0].id in {"dcr","status"})]
        node.args.kwonlyargs=[a for a in node.args.kwonlyargs if a.arg!="unit"]
        # unit was added only as the last required keyword-only parameter.
        if len(node.args.kw_defaults)>len(node.args.kwonlyargs):node.args.kw_defaults.pop()
        return self.generic_visit(node)

    def visit_Call(self,node):
        is_result=(isinstance(node.func,ast.Name) and node.func.id=="CheckResult" or
                   isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name)
                   and node.func.value.id=="CheckResult" and node.func.attr=="from_values")
        if is_result:
            node.func=ast.Name(id="RESULT_TRANSPORT",ctx=ast.Load())
            node.keywords=[k for k in node.keywords if k.arg not in {"dcr","status","unit"}]
            for k in node.keywords:
                if k.arg in {"demand","capacity"} and isinstance(k.value,ast.Call) and isinstance(k.value.func,ast.Name) and k.value.func.id=="round":
                    assert len(k.value.args)==2 and isinstance(k.value.args[1],ast.Constant) and k.value.args[1].value==3
                    k.value=k.value.args[0]
        elif isinstance(node.func,ast.Name) and node.func.id=="_build_result":
            node.keywords=[k for k in node.keywords if k.arg!="unit"]
        return self.generic_visit(node)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git',required=True)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--capture',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():raise SystemExit("Use a new evidence path")
    def git(*values):
        p=subprocess.run([args.git,*values],capture_output=True)
        assert p.returncode==0,p.stderr.decode(errors='replace')
        return p.stdout
    head=git('rev-parse','HEAD').decode().strip()
    assert head=='dbd87cbd6874073750925125fb2db262f2af6f04'
    assert git('branch','--show-current').decode().strip()=='main'
    assert not git('diff','--cached','--name-only')
    git('diff','--check')
    tracked=git('ls-files','-z').decode().split('\0')
    allowed={'src/steel_design/models.py','src/steel_design/run.py',
             'tests/test_hfs000_characterization.py','tests/test_engine_cli_integration.py'}
    rules=list(Path('src/steel_design/domain/rules').glob('*.py'))
    allowed.update(p.as_posix() for p in rules)
    protected={}
    for name in tracked:
        if not name or name in allowed:continue
        if (name.startswith(('src/','examples/','data/','docs/audit/')) or
            name in {'a360-22w.pdf','a341-22w.pdf'} or
            name.startswith('tests/test_')) and name!='docs/audit/tracking.md':
            # Historical fixture directories with known ACL restrictions are not inspected.
            if '/.tmp_tests/' in name:continue
            data=Path(name).read_bytes(); original=git('show','HEAD:'+name)
            assert data.replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),name
            protected[name]=hashlib.sha256(data).hexdigest()
    normalized={}
    for path in rules:
        old=ast.parse(git('show','HEAD:'+path.as_posix()).decode('utf-8'))
        new=ast.parse(path.read_text(encoding='utf-8'))
        assert ast.dump(ResultTransport().visit(old))==ast.dump(ResultTransport().visit(new)),path
        normalized[path.as_posix()]='identical AST except result construction/decision and explicit unit keywords'
    inputs=json.loads((args.capture/'copied_inputs.json').read_text())
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in inputs.items())
    status=subprocess.run([args.git,'status','--short','--untracked-files=all'],capture_output=True,text=True,encoding='utf-8')
    report=dict(head=head,branch='main',index_unchanged=True,diff_check_exit=0,
                protected_files=protected,rules_comparison=normalized,
                capture_inputs_match=True,status_command=[args.git,'status','--short','--untracked-files=all'],
                status=status.stdout,access_warnings=status.stderr)
    write_json(args.out,report)
    print(f"Verified {len(protected)} protected files, six rule modules and capture hashes")
