import sys 
import logging
from pathlib import Path

from iam_bt.bt import QueryNode, While, FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode
from iam_bt.mock_domain_query import MockPenInJarDomainClient
from iam_bt.utils import run_tree

class HumanKeepExecConditionNode(ConditionNode):

    def _eval(self, state):
        return state['human:exec/all']

class HumanExecSkillConditionNode(ConditionNode):

    def __init__(self, skill_name):
        super().__init__()
        self.exec_skill_name = skill_name

    def _eval(self, state):
        return state['human:exec/{}'.format(self.exec_skill_name)]


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

    fh = logging.FileHandler('pen_in_jar.log', 'w+')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - {%(filename)s:%(funcName)s:%(lineno)d} - %(message)s')
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.info('Creating tree')
    
    old_tree = FallBack([
        NegationDecorator(PenOnTableConditionNode()),
        Sequence([
            SkillNode('reset'),
            SkillNode('grasp', GraspPenParamSelector()),
            SkillNode('move_ee_to_pose', MovePenAboveJarParamSelector()),
            SkillNode('open_gripper'),
            SkillNode('reset')
        ])
    ])

    tree = While([
        HumanKeepExecConditionNode(),
        Sequence([
            Sequence([
                QueryNode('reset'),
                QueryNode('grasp'),
                QueryNode('move_ee_to_pose'),
                QueryNode('open_gripper'),
            ]),
            FallBack([
                Sequence([
                    HumanExecSkillConditionNode('reset'),
                    SkillNode('reset'),
                ]),
                Sequence([
                    HumanExecSkillConditionNode('grasp'),
                    SkillNode('grasp'),
                ]),
                Sequence([
                    HumanExecSkillConditionNode('move_ee_to_pose'),
                    SkillNode('move_ee_to_pose'),
                ]),
                Sequence([
                    HumanExecSkillConditionNode('open_gripper'),
                    SkillNode('open_gripper'),
                ]),
            ]),
        ]),
    ])

    tree = Sequence([
        Sequence([
            QueryNode('reset'),
            QueryNode('grasp'),
            QueryNode('move_ee_to_pose'),
            QueryNode('open_gripper'),
        ]),
        While([
            HumanKeepExecConditionNode(),
            FallBack([
                Sequence([
                    QueryNode('reset'),
                    HumanExecSkillConditionNode('reset'),
                    SkillNode('reset'),
                ]),
                Sequence([
                    QueryNode('grasp'),
                    HumanExecSkillConditionNode('grasp'),
                    SkillNode('grasp'),
                ]),
                Sequence([
                    QueryNode('move_ee_to_pose'),
                    HumanExecSkillConditionNode('move_ee_to_pose'),
                    SkillNode('move_ee_to_pose'),
                ]),
                Sequence([
                    QueryNode('open_gripper'),
                    HumanExecSkillConditionNode('open_gripper'),
                    SkillNode('open_gripper'),
                ]),
            ]),
        ]),
    ])
    

    logging.info('Creating mock domain')
    domain = MockPenInJarDomainClient()

    save_dir = Path('pen_in_jar')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(tree, domain, save_dir=save_dir)
