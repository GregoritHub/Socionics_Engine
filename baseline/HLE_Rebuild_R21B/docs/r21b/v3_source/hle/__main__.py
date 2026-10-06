"""Run the unchanged R15 workshop with R16A joint assessment."""
import json
from . import __version__
from .shell_demo import case
from .compensation_evaluation import evaluate

def main():
    world,setup=case()
    report=evaluate(world,setup)
    fields=('events','logical_work','maintained_optional_engagements','correct_optional_endpoints',
            'optional_release_work_by_item','final_dependency','oracle_errors','shell_assessment','clearance_assessment')
    print(json.dumps({'version':__version__,'milestone':'R16A',**{k:report[k] for k in fields if k!='shell_assessment'},
        'shell_assessment':[{s:row['status'] for s,row in g['signs'].items()} for g in world.shell_report()['groups']],
        'parent_R16_complete':False,'remaining_parent_milestones':6},indent=2))

if __name__=='__main__':main()
