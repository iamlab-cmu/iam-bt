import sys 
import json
import yaml
import logging
from pathlib import Path

from iam_bt.bt import QueryNode, While, FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode, GetSkillTrajNode, ResolveButtonNode
from iam_bt.utils import run_tree, assign_unique_name
from iam_domain_handler.domain_client import DomainClient 


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)

    fh = logging.FileHandler('query_trajs.log', 'w+')
    # fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - {%(filename)s:%(funcName)s:%(lineno)d} - %(message)s')
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.info('Creating tree')
    
    fname = 'examples/query_trajs.yaml'
    query_param_dict = yaml.load(open(fname, 'r'), Loader=yaml.FullLoader)
    query_param_dict = assign_unique_name(query_param_dict)

    simple_tree = Sequence([
        GetSkillTrajNode('stay_in_place', GraspPenParamSelector()),
        GetSkillTrajNode('stay_in_place', GraspPenParamSelector()),
        QueryNode('query_trajs', json.dumps(query_param_dict)),
    ])
    
    logging.info('Creating mock domain')
    domain = DomainClient()

    save_dir = Path('query_trajs')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(simple_tree, domain, save_dir=save_dir)