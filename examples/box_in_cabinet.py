import logging
from pathlib import Path

from iam_bt.bt import FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode
from iam_bt.mock_domain import MockBoxInCabinetDomainHandlerClient
from iam_bt.utils import run_tree


class BoxOnTableConditionNode(ConditionNode):

    def _eval(self, state):
        return state['frame:box:pose/position'][2] < 0.1


class CabinetOpenConditionNode(ConditionNode):

    def _eval(self, state):
        return state['frame:cabinet:open'][0]


class OpenCabinetParamSelector(SkillParamSelector):

    def __call__(self, state):
        return 'frame:cabinet:handle'


class GraspBoxParamSelector(SkillParamSelector):

    def __call__(self, state):
        return 'frame:box'


class MoveBoxInCabinetParamSelector(SkillParamSelector):

    def __call__(self, state):
        return 'frame:cabinet'


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)

    logging.info('Creating tree')
    tree = FallBack([
        NegationDecorator(BoxOnTableConditionNode()),
        Sequence([
            SkillNode('reset'),
            FallBack([
                CabinetOpenConditionNode(),
                SkillNode('open', OpenCabinetParamSelector())
            ]),
            SkillNode('grasp', GraspBoxParamSelector()),
            SkillNode('move_ee_to_pose', MoveBoxInCabinetParamSelector()),
            SkillNode('open_gripper'),
            SkillNode('reset')
        ])
    ])

    logging.info('Creating mock domain')
    domain = MockBoxInCabinetDomainHandlerClient()

    save_dir = Path('box_in_cabinet')
    logging.info(f'Running tree and saving viz to {save_dir}')
    run_tree(tree, domain, save_dir=save_dir)
