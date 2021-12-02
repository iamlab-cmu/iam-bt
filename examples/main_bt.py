import sys 
import json
import yaml
import logging
from pathlib import Path

from iam_bt.bt import QueryNode, While, FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode, GetSkillTrajNode, ResolveQueryNode, SaveImageNode
from iam_bt.utils import run_tree, assign_unique_name
from iam_domain_handler.domain_client import DomainClient 

class ButtonPushedConditionNode(ConditionNode):

    def __init__(self, state_field_name):
        super().__init__()
        self._state_field_name = state_field_name

    def _eval(self, state):
        return self._state_field_name in self.blackboard['query_response']['button_inputs'].keys() \
               and self.blackboard['query_response']['button_inputs'][self._state_field_name] > 0

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)

    fh = logging.FileHandler('main_bt.log', 'w+')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - {%(filename)s:%(funcName)s:%(lineno)d} - %(message)s')
    fh.setFormatter(formatter)
    logging.getLogger().addHandler(fh)

    logging.info('Creating tree')

    main_menu_query_params = {
        'display_type' : 0, 
        'buttons' : [
            {
                'name' : 'Teach Skill',
                'text' : '',
            },
            {
                'name' : 'Replay Trajectory',
                'text' : '',
            },
            {
                'name' : 'Execute DMP Skill',
                'text' : '',
            },
            {
                'name' : 'Save Images',
                'text' : '',
            },
            {
                'name' : 'Label Images',
                'text' : '',
            },
            {
                'name' : 'Select Point Goals',
                'text' : '',
            },
        ]
    }

    teach_skill_tree = Sequence([ButtonPushedConditionNode('Teach Skill'),
                                ])

    replay_trajectory_tree = Sequence([ButtonPushedConditionNode('Replay Trajectory'),
                                      ])

    execute_dmp_skill_tree = Sequence([ButtonPushedConditionNode('Execute DMP Skill'),
                                      ])

    save_images_1_query_params = {
        'instruction_text' : 'Press Save when you want to save images. Else press Done when you have finished.',
        'buttons' : [
            {
                'name' : 'Save',
                'text' : '',
            },
            {
                'name' : 'Done',
                'text' : '',
            },
        ]
    }

    save_images_skill_tree = Sequence([ButtonPushedConditionNode('Save Images'),
                                       QueryNode('save_images_1', save_images_1_query_params),
                                       ResolveQueryNode('save_images_1', save_images_1_query_params),
                                       While([ButtonPushedConditionNode('Save'), 
                                              Sequence([SaveImageNode('/rgb/image_raw'),
                                                        QueryNode('save_images_n', save_images_1_query_params),
                                                        ResolveQueryNode('save_images_n', save_images_1_query_params)])
                                             ])
                                      ])

    label_images_skill_tree = Sequence([ButtonPushedConditionNode('Label Images'),
                                       ])

    select_point_goals_tree = Sequence([ButtonPushedConditionNode('Select Point Goals'),
                                       ])

    main_menu_tree = Sequence([
        QueryNode('main_menu', main_menu_query_params),
        ResolveQueryNode('main_menu', main_menu_query_params),
        FallBack([
            teach_skill_tree,
            replay_trajectory_tree,
            execute_dmp_skill_tree,
            save_images_skill_tree,
            label_images_skill_tree,
            select_point_goals_tree,
        ])
    ])
    
    logging.info('Creating mock domain')
    domain = DomainClient()

    save_dir = Path('main_bt')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(main_menu_tree, domain, save_dir=save_dir)