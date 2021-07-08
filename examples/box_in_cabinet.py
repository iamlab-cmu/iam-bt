from iam_bt.bt import FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode, run_tree
from iam_bt.mock_domain import MockBoxInCabinetDomainHandlerClient


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

    tree.save_graph_vis('box_in_cabinet.png')

    domain = MockBoxInCabinetDomainHandlerClient()
    run_tree(tree, domain)
