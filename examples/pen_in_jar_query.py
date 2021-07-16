import sys 
import json
import logging
from pathlib import Path

from iam_bt.bt import QueryNode, While, FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode
from iam_bt.mock_domain_query import MockPenInJarWithQueryDomainClient
from iam_bt.utils import run_tree, assign_unique_name


class ButtonPushedConditionNode(ConditionNode):

    def __init__(self, button_idx):
        super().__init__()
        # self.button_name = button_name
        self.button_idx = button_idx

    def _eval(self, state):
        return state['clicked_button_index'][0] == self.button_idx


class PenOnTableConditionNode(ConditionNode):

    def _eval(self, state):
        return state['frame:pen:pose/position'][2] < 0.1


class GraspPenParamSelector(SkillParamSelector):

    def __call__(self, state):
        return 'frame:box'


class MovePenAboveJarParamSelector(SkillParamSelector):

    def __call__(self, state):
        return 'frame:jar'


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)

    fh = logging.FileHandler('pen_in_jar_query.log', 'w+')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - {%(filename)s:%(funcName)s:%(lineno)d} - %(message)s')
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.info('Creating tree')
    
    query_param_dict = {
        'buttons' : [
            {
                'name' : 'grasp_button',
                'text' : 'Execute Grasp Skill',
            },
            {
                'name' : 'move_ee_to_pose_button',
                'text' : 'Execute Move EE to Pose Skill',
            },
            {
                'name' : 'stop_button',
                'text' : 'Click this to terminate behavior tree',
            },
        ]
    }
    query_param_dict = assign_unique_name(query_param_dict)

    simple_tree = While([
        NegationDecorator(ButtonPushedConditionNode(2)),
        Sequence([
            QueryNode(' ', json.dumps(query_param_dict)),
            FallBack([
                Sequence([
                    ButtonPushedConditionNode(0),
                    SkillNode('grasp'),
                ]),
                Sequence([
                    ButtonPushedConditionNode(1),
                    SkillNode('move_ee_to_pose'),
                ]),
            ])
        ])
    ])
    
    
    logging.info('Creating mock domain')
    domain = MockPenInJarWithQueryDomainClient()

    save_dir = Path('pen_in_jar_query')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(simple_tree, domain, save_dir=save_dir)