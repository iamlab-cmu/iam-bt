import logging
from pathlib import Path

from iam_bt.bt import Parallel, SkillNode, ConditionNode, SkillParamSelector, SkillNode
from iam_bt.mock_domain import MockPenInJarParallelDomainClient
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
    logging.getLogger().setLevel(logging.DEBUG)

    fh = logging.FileHandler('pen_in_jar_parallel.log', 'w+')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - {%(filename)s:%(funcName)s:%(lineno)d} - %(message)s')
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.info('Creating tree')

    tree = Parallel([
        SkillNode('reset'),
        SkillNode('grasp', GraspPenParamSelector()),
        SkillNode('move_ee_to_pose', MovePenAboveJarParamSelector()),
        SkillNode('open_gripper'),
    ], 4)

    logging.info('Creating mock domain')
    domain = MockPenInJarParallelDomainClient()

    save_dir = Path('pen_in_jar_parallel')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(tree, domain, save_dir=save_dir, skip_running_nodes=False)
