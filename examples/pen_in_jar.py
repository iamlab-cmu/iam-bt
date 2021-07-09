import logging
from pathlib import Path

from iam_bt.bt import FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode
from iam_bt.mock_domain import MockPenInJarDomainClient
from iam_bt.utils import run_tree


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
    logging.getLogger().setLevel(logging.INFO)

    logging.info('Creating tree')
    tree = FallBack([
        NegationDecorator(PenOnTableConditionNode()),
        Sequence([
            SkillNode('reset'),
            SkillNode('grasp', GraspPenParamSelector()),
            SkillNode('move_ee_to_pose', MovePenAboveJarParamSelector()),
            SkillNode('open_gripper'),
            SkillNode('reset')
        ])
    ])

    logging.info('Creating mock domain')
    domain = MockPenInJarDomainClient()

    save_dir = Path('pen_in_jar')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(tree, domain, save_dir=save_dir)
