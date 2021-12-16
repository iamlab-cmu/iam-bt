import sys 
import json
import yaml
import logging
from pathlib import Path

from iam_bt.bt import *
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
        'instruction_text' : 'Select one of the options below.',
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

    reposition_robot_1_query_params = {
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

    reposition_robot_2_query_params = {
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

    reposition_robot_3_query_params = {
        'instruction_text' : 'If you are done repositioning the robot, press Done. Otherwise to continue repositioning, press Reposition.',
        'buttons' : [
            {
                'name' : 'Done',
                'text' : '',
            },
            {
                'name' : 'Reposition',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ]
    }

    parallel_reposition_tree = Parallel([Sequence([QueryNode('Reposition 2', reposition_robot_2_query_params),
                                                   ResolveQueryNode('Reposition 2', reposition_robot_2_query_params),
                                                   CancelSkillNode(),
                                                  ]),
                                         Sequence([SkillNode('zero_force', zero_force_skill_params),
                                                   CancelQueryNode()
                                                  ])
                                        ], 1)

    reposition_robot_skill_tree = Sequence([QueryNode('Reposition 1', reposition_robot_1_query_params),
                                            ResolveQueryNode('Reposition 1', reposition_robot_1_query_params),
                                            FallBack([Sequence([ButtonPushedConditionNode('Start'),
                                                                parallel_reposition_tree,
                                                                FallBack([ButtonPushedConditionNode('Done'),
                                                                          ButtonPushedConditionNode('Cancel'),
                                                                          Sequence([QueryNode('Reposition 3', reposition_robot_3_query_params),
                                                                                    ResolveQueryNode('Reposition 3', reposition_robot_3_query_params),
                                                                                    FallBack([While([ButtonPushedConditionNode('Reposition'),
                                                                                                     Sequence([parallel_reposition_tree,
                                                                                                               FallBack([ButtonPushedConditionNode('Done'),
                                                                                                                         ButtonPushedConditionNode('Cancel'),
                                                                                                                         Sequence([QueryNode('Reposition 3', reposition_robot_3_query_params),
                                                                                                                                   ResolveQueryNode('Reposition 3', reposition_robot_3_query_params),
                                                                                                                                  ])
                                                                                                                        ])
                                                                                                              ])
                                                                                                    ]),
                                                                                              NegationDecorator(ButtonPushedConditionNode('Reposition'))
                                                                                             ]),
                                                                                   ]),
                                                                          
                                                                         ])
                                                               ])
                                                      
                                                     ])
                                           ])

    record_trajectory_query_params = {
        'instruction_text' : 'Press Done when Completed.',
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

    record_trajectory_skill_params = {
        'duration' : 10,
        'dt' : 0.01
    }

    parallel_record_trajectory_tree = Parallel([Sequence([QueryNode('Record Trajectory 1', record_trajectory_query_params),
                                                          ResolveQueryNode('Record Trajectory 1', record_trajectory_query_params),
                                                          CancelSkillNode(),
                                                         ]),
                                                Sequence([SkillNode('record_trajectory', record_trajectory_skill_params),
                                                          CancelQueryNode()
                                                         ])
                                                ], 1)

    teaching_1_query_params = {
        'instruction_text' : 'Enter the name of the skill and its duration. Then hold onto the robot and press Start.',
        'buttons' : [
            {
                'name' : 'Start',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ],
        'text_inputs' : [
            {
                'name' : 'skill_name',
                'text' : 'Skill Name',
                'value' : '',
            },
            {
                'name' : 'skill_duration',
                'text' : 'Skill Duration',
                'value' : '10',
            },
        ]
    }

    teaching_2_query_params = {
        'instruction_text' : 'Press Ok if the recorded trajectory looks good.',
        'display_type' : 2,
        'camera_topic' : '/rgb/image_raw',
        'buttons' : [
            {
                'name' : 'Ok',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ],
    }

    teaching_3_query_params = {
        'instruction_text' : 'Truncate the trajectory.',
        'display_type' : 3,
        'bokeh_display_type' : 0,
    }

    teach_skill_tree = Sequence([ButtonPushedConditionNode('Teach Skill'),
                                 reposition_robot_skill_tree,
                                 FallBack([Sequence([ButtonPushedConditionNode('Done'),
                                                     QueryNode('Teaching 1', teaching_1_query_params),
                                                     ResolveQueryNode('Teaching 1', teaching_1_query_params),
                                                     ButtonPushedConditionNode('Start'),
                                                     SaveTextInputToBlackBoardNode('skill_name', 'skill_name'),
                                                     SaveTextInputToBlackBoardNode('skill_duration', 'skill_duration'),
                                                     parallel_record_trajectory_tree,
                                                     FallBack([ButtonPushedConditionNode('Cancel'),
                                                               Sequence([SaveMemoryToBlackBoardNode('recorded_trajectory', 'recorded_trajectory'),
                                                                         QueryNode('Teaching 2', teaching_2_query_params),
                                                                         ResolveQueryNode('Teaching 2', teaching_2_query_params),
                                                                         ButtonPushedConditionNode('Ok'),
                                                                         QueryNode('Teaching 3', teaching_3_query_params),
                                                                         ResolveQueryNode('Teaching 3', teaching_3_query_params),
                                                                         SaveTrajectoryInfoToMemoryNode(),
                                                                         ClearMemoryNode('recorded_trajectory')
                                                                        ])])
                                                    ]),
                                           ButtonPushedConditionNode('Cancel')
                                          ])
                                ])

    replay_1_query_params = {
        'instruction_text' : 'Enter the name of the skill, move away from the robot, and press Start.',
        'buttons' : [
            {
                'name' : 'Start',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ],
        'text_inputs' : [
            {
                'name' : 'skill_name',
                'text' : 'Skill Name',
                'value' : '',
            }
        ]
    }

    go_to_start_query_params = {
        'instruction_text' : 'The robot will first move to the starting point of the saved skill.',
        'buttons' : [
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ]
    }

    go_to_start_skill_params = {
        'duration' : 5,
        'dt' : 0.01,
    }

    parallel_go_to_start_tree = Parallel([Sequence([QueryNode('Go To Start 1', go_to_start_query_params),
                                                    ResolveQueryNode('Go To Start 1', go_to_start_query_params),
                                                    CancelSkillNode(),
                                                    ]),
                                          Sequence([SkillNode('go_to_start', go_to_start_skill_params),
                                                    CancelQueryNode()
                                                   ])
                                         ], 1)

    replay_2_query_params = {
        'instruction_text' : 'The robot will execute the saved skill.',
        'buttons' : [
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ]
    }

    replay_trajectory_skill_params = {
        'dt' : 0.02,
    }

    parallel_replay_trajectory_tree = Parallel([Sequence([QueryNode('Replay 2', replay_2_query_params),
                                                          ResolveQueryNode('Replay 2', replay_2_query_params),
                                                          CancelSkillNode(),
                                                         ]),
                                                Sequence([SkillNode('replay_trajectory', replay_trajectory_skill_params),
                                                          CancelQueryNode()
                                                         ])
                                               ], 1)

    replay_trajectory_tree = Sequence([ButtonPushedConditionNode('Replay Trajectory'),
                                       reposition_robot_skill_tree,
                                       FallBack([Sequence([ButtonPushedConditionNode('Done'),
                                                           QueryNode('Replay 1', replay_1_query_params),
                                                           ResolveQueryNode('Replay 1', replay_1_query_params),
                                                           ButtonPushedConditionNode('Start'),
                                                           SaveTextInputToBlackBoardNode('skill_name', 'skill_name'),
                                                           SaveMemoryToBlackBoardNode('<skill_name>', '<skill_name>'),
                                                           parallel_go_to_start_tree,
                                                           NegationDecorator(ButtonPushedConditionNode('Cancel')),
                                                           parallel_replay_trajectory_tree,
                                                          ]),
                                                 ButtonPushedConditionNode('Cancel')
                                                ])
                                      ])

    execute_dmp_1_query_params = {
        'instruction_text' : 'Enter the name of the skill, move away from the robot, and press Start.',
        'buttons' : [
            {
                'name' : 'Start',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ],
        'text_inputs' : [
            {
                'name' : 'skill_name',
                'text' : 'Skill Name',
                'value' : '',
            }
        ]
    }

    execute_dmp_2_query_params = {
        'instruction_text' : 'The robot will execute the saved skill.',
        'buttons' : [
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ]
    }

    execute_dmp_trajectory_skill_params = {
        'dt' : 0.01,
    }

    parallel_execute_dmp_trajectory_tree = Parallel([Sequence([QueryNode('execute_dmp 2', execute_dmp_2_query_params),
                                                               ResolveQueryNode('execute_dmp 2', execute_dmp_2_query_params),
                                                               CancelSkillNode(),
                                                              ]),
                                                     Sequence([SkillNode('execute_dmp_trajectory', execute_dmp_trajectory_skill_params),
                                                               CancelQueryNode()
                                                              ])
                                                     ], 1)

    execute_dmp_skill_tree = Sequence([ButtonPushedConditionNode('Execute DMP Skill'),
                                       reposition_robot_skill_tree,
                                       FallBack([Sequence([ButtonPushedConditionNode('Done'),
                                                           QueryNode('Execute DMP 1', execute_dmp_1_query_params),
                                                           ResolveQueryNode('Execute DMP 1', execute_dmp_1_query_params),
                                                           ButtonPushedConditionNode('Start'),
                                                           SaveTextInputToBlackBoardNode('skill_name', 'skill_name'),
                                                           SaveMemoryToBlackBoardNode('<skill_name>', '<skill_name>'),
                                                           parallel_execute_dmp_trajectory_tree
                                                          ]),
                                                 ButtonPushedConditionNode('Cancel')
                                                ])
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
                                                        Sequence([SaveImageNode('/rgb/image_raw', 'rgb', True, False),
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
                                        GetImageNode(False),
                                        QueryNode('label_image', label_images_query_params),
                                        ResolveQueryNode('label_image', label_images_query_params),
                                        SaveMasksNode(),
                                        FallBack([While([ButtonPushedConditionNode('request_next_image'), 
                                                         Sequence([GetImageNode(False),
                                                                   QueryNode('label_image', label_images_query_params),
                                                                   ResolveQueryNode('label_image', label_images_query_params),
                                                                   SaveMasksNode()
                                                                  ])
                                                        ]),
                                                  NegationDecorator(ButtonPushedConditionNode('request_next_image'))
                                                 ])
                                       ])

    select_points_1_query_params = {
        'instruction_text' : 'Click points on the image corresponding to goal locations for an object. Press submit when done.',
        'display_type' : 3,
        'bokeh_display_type' : 2
    }

    select_points_2_query_params = {
        'instruction_text' : 'Press Start when you are safely away from the robot.',
        'buttons' : [
            {
                'name' : 'Start',
                'text' : '',
            },
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ],
    }

    pick_and_place_query_params = {
        'instruction_text' : 'Press Cancel if you would like to stop the robot.',
        'buttons' : [
            {
                'name' : 'Cancel',
                'text' : '',
            },
        ]
    }

    reset_arm_skill_params = {
        'duration' : 5,
        'dt' : 0.01,
    }

    intermediate_pose_skill_params = {
        'duration' : 5,
        'dt' : 0.01,
        'goal_pose' : 'intermediate'
    }

    grasp_pose_skill_params = {
        'duration' : 5,
        'dt' : 0.01,
        'goal_pose' : 'grasp'
    }

    pick_and_place_tree = Parallel([Sequence([QueryNode('Pick and Place 1', pick_and_place_query_params),
                                              ResolveQueryNode('Pick and Place 1', pick_and_place_query_params),
                                              CancelSkillNode(),
                                             ]),
                                    Sequence([GenerateGoalPointsNode(),
                                              GeneratePickAndPlacePositionsNode(),
                                              SkillNode('reset_arm', reset_arm_skill_params),
                                              SkillNode('one_step_pose', intermediate_pose_skill_params),
                                              SkillNode('one_step_pose', grasp_pose_skill_params),
                                              SkillNode('close_gripper', {}),
                                              SkillNode('one_step_pose', intermediate_pose_skill_params),
                                              SkillNode('one_step_pose', grasp_pose_skill_params),
                                              SkillNode('open_gripper', {}),
                                              SkillNode('one_step_pose', intermediate_pose_skill_params),
                                              SkillNode('reset_arm', reset_arm_skill_params),
                                              CancelQueryNode()
                                             ])
                                   ], 1)

    

    select_points_tree = Sequence([ButtonPushedConditionNode('Select Point Goals'),
                                   SaveImageNode('/rgb/image_raw', 'rgb', True, False),
                                   GenerateDepthImagePathNode(),
                                   SaveImageNode('/depth_to_rgb/image_raw', 'depth', False, True),
                                   GetImageNode(True),  
                                   QueryNode('Select Points 1', select_points_1_query_params),
                                   ResolveQueryNode('Select Points 1', select_points_1_query_params),
                                   SaveQueryItemToBlackBoardNode('desired_positions', 'desired_positions'),
                                   QueryNode('Select Points 2', select_points_2_query_params),
                                   ResolveQueryNode('Select Points 2', select_points_2_query_params),
                                   FallBack([Sequence([ButtonPushedConditionNode('Start'),
                                                       pick_and_place_tree
                                                      ]),
                                             ButtonPushedConditionNode('Cancel'),
                                            ])
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
            select_points_tree,
        ])
    ])])
    
    logging.info('Creating mock domain')
    domain = DomainClient()

    save_dir = Path('main_bt')
    logging.info(f'Running tree and saving viz to {save_dir}...')
    run_tree(main_menu_tree, domain, save_dir=save_dir)