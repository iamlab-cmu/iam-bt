import sys 
import json
import yaml
import logging
from pathlib import Path

from iam_bt.bt import QueryNode, While, FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode, GetSkillTrajNode, ResolveButtonNode
from iam_bt.utils import run_tree, assign_unique_name
from iam_domain_handler.domain_client import DomainClient 

class ButtonPushedConditionNode(ConditionNode):

    def __init__(self, state_field_name):
        super().__init__()
        self._state_field_name = state_field_name

    def _eval(self, state):
        return self.blackboard[self._state_field_name] > 0

class GraspPenParamSelector(SkillParamSelector):

    def __call__(self, state):
        return 'frame:box'


class MovePenAboveJarParamSelector(SkillParamSelector):

    def __call__(self, state):
        return 'frame:jar'

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)

    fh = logging.FileHandler('query_buttons.log', 'w+')
    # fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - {%(filename)s:%(funcName)s:%(lineno)d} - %(message)s')
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.info('Creating tree')
    
    fname = 'examples/query_buttons.yaml'
    query_param_dict = yaml.load(open(fname, 'r'), Loader=yaml.FullLoader)
    query_param_dict = assign_unique_name(query_param_dict)

    query_button_tree = QueryNode('query_buttons', json.dumps(query_param_dict))
    simple_tree = Sequence([
        query_button_tree,
        ResolveButtonNode('query_buttons', json.dumps(query_param_dict)),
        FallBack([
            ButtonPushedConditionNode(query_param_dict["buttons"][0]['name']),
            ButtonPushedConditionNode(query_param_dict["buttons"][1]['name']),
        ])
    ])
    
    logging.info('Creating mock domain')
    domain = DomainClient()

    save_dir = Path('pen_in_jar_traj')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(simple_tree, domain, save_dir=save_dir)