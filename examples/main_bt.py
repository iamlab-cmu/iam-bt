import sys 
import json
import yaml
import logging
from pathlib import Path

from iam_bt.bt import QueryNode, While, FallBack, Sequence, NegationDecorator, ConditionNode, SkillParamSelector, SkillNode, GetSkillTrajNode, ResolveQueryNode, SaveImageNode, GetImageNode, Parallel, SaveMasksNode, CancelQueryNode, CancelSkillNode
from iam_bt.utils import run_tree, assign_unique_name
from iam_domain_handler.domain_client import DomainClient 

class ButtonPushedConditionNode(ConditionNode):

    def __init__(self, state_field_name):
        super().__init__()
        self._state_field_name = state_field_name

    def _eval(self, state):
        return self._state_field_name in self.blackboard['query_response']['button_inputs'].keys() \
               and self.blackboard['query_response']['button_inputs'][self._state_field_name] > 0

class BoolConditionNode(ConditionNode):

    def __init__(self, state_field_name):
        super().__init__()
        self._state_field_name = state_field_name

    def _eval(self, state):
        return self._state_field_name == 'true' or self.blackboard[self._state_field_name]

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

    teach_skill_1_query_params = {
        'instruction_text' : 'Hold onto the robot and press the Start button to Move the Robot to the Starting Position.',
        'buttons' : [
            {
                'name' : 'Start',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ]
    }

    zero_force_skill_params = {
        'duration' : 10,
        'dt' : 0.01
    }

    reposition_robot_query_params = {
        'instruction_text' : 'Move the Robot to the Starting Position and Press Done when Completed.',
        'buttons' : [
            {
                'name' : 'Done',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ]
    }

    reposition_robot_skill_tree = Parallel([Sequence([SkillNode('zero_force', zero_force_skill_params),
                                                      CancelQueryNode()
                                                     ]),
                                            Sequence([QueryNode('Teach Skill 2', reposition_robot_query_params),
                                                      ResolveQueryNode('Teach Skill 2', reposition_robot_query_params),
                                                      CancelSkillNode(),
                                                     ])], 1)

    teach_skill_tree = Sequence([ButtonPushedConditionNode('Teach Skill'),
                                 QueryNode('Teach Skill 1', teach_skill_1_query_params),
                                 ResolveQueryNode('Teach Skill 1', teach_skill_1_query_params),
                                 ButtonPushedConditionNode('Start'),
                                 reposition_robot_skill_tree,
                                 ButtonPushedConditionNode('Done'),

                                 ])

    replay_trajectory_tree = Sequence([ButtonPushedConditionNode('Replay Trajectory'),
                                      ])

    execute_dmp_skill_tree = Sequence([ButtonPushedConditionNode('Execute DMP Skill'),
                                      ])

    save_images_query_params = {
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
                                       QueryNode('save_images', save_images_query_params),
                                       ResolveQueryNode('save_images', save_images_query_params),
                                       FallBack([While([ButtonPushedConditionNode('Save'), 
                                                        Sequence([SaveImageNode('/rgb/image_raw'),
                                                                  QueryNode('save_images', save_images_query_params),
                                                                  ResolveQueryNode('save_images', save_images_query_params)
                                                                 ])
                                                       ]),
                                                 ButtonPushedConditionNode('Done') 
                                                ])
                                      ])

    label_images_query_params = {
        'instruction_text' : 'Label the image. Press submit when you are done labeling an image.',
        'display_type' : 3,
        'bokeh_display_type' : 1
    }

    label_images_skill_tree = Sequence([ButtonPushedConditionNode('Label Images'),
                                        GetImageNode(),
                                        QueryNode('label_image', label_images_query_params),
                                        ResolveQueryNode('label_image', label_images_query_params),
                                        SaveMasksNode(),
                                        FallBack([While([BoolConditionNode('request_next_image'), 
                                                         Sequence([GetImageNode(),
                                                                   QueryNode('label_image', label_images_query_params),
                                                                   ResolveQueryNode('label_image', label_images_query_params),
                                                                   SaveMasksNode()
                                                                  ])
                                                        ]),
                                        ])
                                       ])

    select_point_goals_tree = Sequence([ButtonPushedConditionNode('Select Point Goals'),
                                       ])

    main_menu_tree = While([BoolConditionNode('true'),
        Sequence([
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
    ])])
    
    logging.info('Creating mock domain')
    domain = DomainClient()

    save_dir = Path('main_bt')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(main_menu_tree, domain, save_dir=save_dir)