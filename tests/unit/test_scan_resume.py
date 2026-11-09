import ast,asyncio,textwrap,importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,AsyncMock
import pytest

SOURCE=Path(importlib.util.find_spec('app.pipeline.runner').origin).read_text()
TREE=ast.parse(SOURCE)
def function(name):
    node=next(n for n in ast.walk(TREE) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    return textwrap.dedent(ast.get_source_segment(SOURCE,node))

@pytest.mark.parametrize('campaign_cancelled,run_cancelled,elapsed,exception',[
    (False,False,0,None),(False,False,10799,None),
    (False,False,10801,TimeoutError),(True,False,0,asyncio.CancelledError),
    (False,True,0,asyncio.CancelledError),
])
def test_resume_budget_and_cancellation(campaign_cancelled,run_cancelled,elapsed,exception):
    conn=Mock()
    def execute(query,args):
        if 'FROM pipeline_runs' in query:
            row={'status':'RUNNING','cancellation_requested':run_cancelled}
        else:
            # Deliberately old campaign, matching the failed production resume.
            row=('2020-01-01T00:00:00+00:00',campaign_cancelled) if 'created_at' in query else (campaign_cancelled,)
        return NS(fetchone=lambda:row)
    conn.execute.side_effect=execute
    env={'run_configuration':{},'time':NS(time=lambda:elapsed),'start_time':0,'self':NS(settings=NS(max_scan_runtime_minutes=180)),
         'conn':conn,'pipeline_run':NS(id=4),'asyncio':asyncio}
    exec(function('runtime_limit')+'\n'+function('check_cancellation'),env)
    if exception:
        with pytest.raises(exception):env['check_cancellation']()
    else:env['check_cancellation']()

def test_pipeline_has_no_assessment_execution_imports():
    forbidden=('app.audit','app.scoring','app.reports','app.enrichment.screenshot')
    imports=[node.module or '' for node in ast.walk(TREE) if isinstance(node,ast.ImportFrom)]
    assert not any(value.startswith(forbidden) for value in imports)
    calls={node.func.id for node in ast.walk(TREE) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
    assert not calls.intersection({'run_lighthouse_audit','perform_quick_audit','analyze_opportunities','capture_website'})
