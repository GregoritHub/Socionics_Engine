"""Finite supplied outcome agendas; expected route names are evaluator labels only."""
from tests_c7_workflow.fixtures import *
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.workflow_selection_records import WorkflowSelectionRequest
from hle_unified.workflow_agenda import WorkflowAgenda

FAMILIES = ('theorize-apply-embody','share-commune-identify','coordinate-mobilize',
            'institutionalize-educate','organize-integrate-apply')


def family(name):
    e = setup_workflow(engine_type=WorkflowFinalSelectionEngine)
    group_ = None
    social = name in FAMILIES[1:4]
    if social:
        group_ = join(e,group(e,'agenda-group'),key='agenda-join')['ref']
        for a in (ALICE,BOB): expose_group(e,a,group_)
    rows = tasks()
    if name == 'coordinate-mobilize':
        rows = (('maintain','care',(),0,2,ALICE),('work','use',('maintain',),1,4,ALICE))
    own = authored(e,'agenda-own',rows,hypothetical=True)
    own_stance = authored(e,'agenda-stance',rows,kind='stance')
    peer_stance = authored(e,'agenda-peer-stance',rows,actor=BOB,kind='stance')
    renewal_peer = peer_stance
    if name == 'share-commune-identify':
        tighter = tuple((t[0],t[1],t[2],t[3],2 if t[0]=='handover' else t[4],t[5]) for t in rows)
        renewal_peer = authored(e,'authored-renewal-stance',tighter,actor=BOB,kind='stance')
    goals=[]
    def goal(sources, priorities, companion='none', externalize=True, peer_stance_ref=None):
        need = seed(e,'agenda-need-'+str(len(goals)),wf.encode(dict(kind='workflow_need',
                    priorities=priorities,externalize=externalize)),relation='c7ws.need',target=DEVICE)
        goals.append(dict(need=need,sources=sources,companion=companion,
                          own_stance=own_stance,peer_stance=peer_stance if peer_stance_ref is None else peer_stance_ref))
    initial=lambda ref:dict(initial=ref)
    prior=lambda n:dict(result=n)
    if name == FAMILIES[0]:
        goal([initial(own)],(10,8,0,9));goal([prior(0)],(10,8,0,9));goal([prior(1)],(10,8,0,9))
    elif name == FAMILIES[1]:
        goal([initial(own)],(0,0,10,0),'exchange')
        goal([prior(0)],(0,0,10,0),'exchange',peer_stance_ref=renewal_peer)
        goal([prior(1),initial(own_stance)],(10,0,0,0))
    elif name == FAMILIES[2]:
        observed=observe(e,'agenda-initial-inspection')
        goal([initial(observed)],(0,0,10,0),'exchange')
        goal([prior(0)],(0,10,0,0))
        goal([prior(1)],(10,0,0,0))
    elif name == FAMILIES[3]:
        # Initial shared contribution and actual practice are native generated inputs.
        shared_, inherited_group=shared(e,'agenda-initial-shared')
        group_=inherited_group
        observation=observe(e,'agenda-initial-care',primitive='care',participants=(BOB,))
        goal([initial(shared_),initial(observation)],(0,0,0,10),externalize=False)
        goal([prior(0)],(0,0,0,10),'votes')
        goal([prior(1)],(0,0,10,0),'exchange')
    elif name == FAMILIES[4]:
        first=observe(e,'agenda-initial-care',primitive='care')
        second=observe(e,'agenda-initial-use',primitive='use')
        goal([initial(own)],(0,0,0,10),externalize=False)
        goal([initial(first),initial(second)],(0,0,0,10))
        goal([prior(0),prior(1)],(0,0,0,10))
        goal([prior(2)],(0,10,0,0))
    else: raise ValueError(name)
    current=e.world.head(DEVICE.identity).ref
    for a in ((ALICE,BOB) if social else (ALICE,)): expose(e,a,current)
    stock=e.world.head(CARE.identity).ref;expose(e,ALICE,stock)
    template=WorkflowSelectionRequest('family',ALICE,ROOM,CUE5,current,goals[0]['need'],
                    (own,),stock=stock,peer=BOB if social else None,group=group_)
    return WorkflowAgenda(e,template,goals)


class WithheldAgenda(WorkflowAgenda):
    """Deliberate downstream access intervention, never ordinary continuation."""
    def step(self):
        before=self.stage
        row=super().step()
        if before==0 and self.stage==1:
            self.results[0]=None
        return row


def withheld(name):
    p=family(name)
    p.__class__=WithheldAgenda
    return p


def terminal_query(p, revised_window=False):
    if p.stage!=len(p.goals) or not p.results or p.results[-1] is None:
        return None
    r=p.template;source=p.results[-1];e=p.engine
    value,_=e._read_workflow(e.participant_view(ALICE),source,WorkflowSelectionRequest(**r))
    domain={'personal':'personal','activity':'activity','shared':'shared','system':'system','rule':'system'}[value['kind']]
    actor=BOB if domain=='shared' else ALICE
    if actor==BOB: expose(e,actor,source)
    kw=dict(peer=ALICE if actor==BOB else r['peer'],group=r['group']) if r['group'] else {}
    output=work(e,request(e,'agenda-fixed-query','use-'+domain,None,(source,),actor=actor,target=r['target'],completed=('maintain',) if revised_window else (),clock=3 if revised_window else 0,**kw))
    return data(e,output,actor)


def renewal_queries(p):
    """Same question of exact before/after generated shared content, both paid."""
    answers=[]
    for index,label in ((0,'before'),(1,'after')):
        source=p.results[index];r=p.template
        out=work(p.engine,request(p.engine,'agenda-renewal-'+label,'use-shared',None,(source,),
            target=r['target'],completed=('maintain',),clock=3,peer=r['peer'],group=r['group']))
        answers.append(data(p.engine,out))
    return answers
