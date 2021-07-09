import logging
from pathlib import Path

from iam_domain_handler.domain_client import DomainClient

from iam_bt.bt import Sequence, SkillNode
from iam_bt.utils import run_tree


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)

    logging.info('Creating tree')
    tree = Sequence([
        SkillNode('close_gripper'),
        SkillNode('open_gripper'),
        SkillNode('stay_in_place'),
    ])

    logging.info('Creating domain')
    domain = DomainClient()

    save_dir = Path('simple_real_domain')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(tree, domain, save_dir=save_dir)
