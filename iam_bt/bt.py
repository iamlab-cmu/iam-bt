import json
from abc import ABC, abstractmethod
from typing import Tuple, Generator
import logging

from shortuuid import uuid
from pydot import Dot, Edge, Node
from pillar_state import State

from .bt_status import BTStatus
from .utils import merge_graphs

import math
import numpy as np
from autolab_core import RigidTransform
from frankapy.utils import convert_rigid_transform_to_array


logger = logging.getLogger(__name__)


class BTNode(ABC):
    # Corresponding information we want to store internally inside the BT
    blackboard = {
        # "buttons" : {},
        # "sliders" : {},
        # "bboxes" : [],
        # "text_inputs" : [],
        # "instruction_text" : [],
        # "camera_topic" : [],
        # "display_type" : [],
        # "traj1" : [],
        # "traj2" : [],
        # "robot" : [],
        # "robot_joint_topic" : [],
    }

    def __init__(self):
        self._uuid_str = f'{self.__class__.__name__}_{uuid()}'

    @property
    def uuid_str(self):
        return self._uuid_str

    @abstractmethod
    def run(self, domain) -> Generator[Tuple['BTNode', BTStatus, BTStatus], None, None]:
        pass

    @abstractmethod
    def get_dot_graph(self) -> Tuple[Node, Dot]:
        pass

    def _create_dot_graph(self):
        return Dot('BT', graph_type='digraph', splines=False)

    def __str__(self):
        return self._uuid_str

class While(BTNode):
    def __init__(self, children):
        super().__init__()
        assert len(children) == 2
        self._condition_child = children[0]
        self._action_child = children[1]
    
    def run(self, domain):
        logger.debug(f'run {self}')
        while True:
            condition_success = False
            status_gen = self._condition_child.run(domain)
            for leaf_node, leaf_status, status in status_gen:
                if status == BTStatus.RUNNING:
                    logger.debug(f'{self} to yield running b/c condition_child {leaf_node} yielded running')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    logger.debug(f'{self} to yield running b/c {leaf_node} yielded success')
                    condition_success = True
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                    break
                elif status == BTStatus.FAILURE:
                    logger.debug(f'{self} to yield failure b/c {leaf_node} yielded failure')
                    yield leaf_node, leaf_status, BTStatus.FAILURE
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if not condition_success:
                logger.debug(f'while failure b/c condition_child failure')
                yield leaf_node, leaf_status, BTStatus.FAILURE
                break

            status_gen = self._action_child.run(domain)
            success = False
            for leaf_node, leaf_status, status in status_gen:
                if status == BTStatus.RUNNING:
                    logger.debug(f'{self} to yield running b/c {leaf_node} yielded running')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    logger.debug(f'{self} to yield running b/c {leaf_node} yielded success')
                    success = True
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                    break
                elif status == BTStatus.FAILURE:
                    logger.debug(f'{self} to yield failure b/c {leaf_node} yielded failure')
                    yield leaf_node, leaf_status, BTStatus.FAILURE
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if not success:
                logger.debug(f'while failure b/c action_child failure')
                yield leaf_node, leaf_status, BTStatus.FAILURE
                break
    
    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label='...', shape='diamond')
        graph.add_node(this_node)

        for child in [self._condition_child, self._action_child]:
            child_root_node, child_graph = child.get_dot_graph()
            merge_graphs(graph, child_graph)
            graph.add_edge(Edge(this_node, child_root_node))

        return this_node, graph


class FallBack(BTNode):

    def __init__(self, children):
        super().__init__()
        assert len(children) > 0
        self._children = children

    def run(self, domain):
        logger.debug(f'run {self}')
        any_child_success = False
        for child in self._children:
            status_gen = child.run(domain)
            success = False
            for leaf_node, leaf_status, status in status_gen:
                if status == BTStatus.RUNNING:
                    logger.debug(f'{self} to yield running b/c {leaf_node} yielded running')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    logger.debug(f'{self} to yield success b/c {leaf_node} yielded success')
                    success = True
                    yield leaf_node, leaf_status, BTStatus.SUCCESS
                    break
                elif status == BTStatus.FAILURE:
                    logger.debug(f'{self} to yield running b/c {leaf_node} yielded failure')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if success:
                any_child_success = True
                break

        if not any_child_success:
            logger.debug(f'{self} to yield failure b/c no children yielded success')
            yield leaf_node, leaf_status, BTStatus.FAILURE

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label='?', shape='square')
        graph.add_node(this_node)

        for child in self._children:
            child_root_node, child_graph = child.get_dot_graph()
            merge_graphs(graph, child_graph)
            graph.add_edge(Edge(this_node, child_root_node))

        return this_node, graph


class Sequence(BTNode):

    def __init__(self, children):
        super().__init__()
        assert len(children) > 0
        self._children = children

    def run(self, domain):
        logger.debug('run sequence')
        
        any_child_failure = False
        for child in self._children:
            status_gen = child.run(domain)
            failure = False
            for leaf_node, leaf_status, status in status_gen:
                if status == BTStatus.RUNNING:
                    logger.debug(f'{self} to yield running b/c {leaf_node} yielded running')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    logger.debug(f'{self} to yield running b/c {leaf_node} yielded success')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                    break
                elif status == BTStatus.FAILURE:
                    logger.debug(f'sequence failure')
                    failure = True
                    logger.debug(f'{self} to yield failure b/c {leaf_node} yielded failure')
                    yield leaf_node, leaf_status, BTStatus.FAILURE
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if failure:
                any_child_failure = True
                break

        if not any_child_failure:
            logger.debug(f'{self} to yield success b/c no child yielded failure')
            yield leaf_node, leaf_status, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label='->', shape='square')
        graph.add_node(this_node)

        for child in self._children:
            child_root_node, child_graph = child.get_dot_graph()
            merge_graphs(graph, child_graph)
            graph.add_edge(Edge(this_node, child_root_node))

        return this_node, graph


class Parallel(BTNode):

    def __init__(self, children, success_threshold):
        super().__init__()
        assert len(children) > 0
        assert success_threshold > 0 and success_threshold <= len(children)
        self._children = children
        self._success_threshold = success_threshold

    def run(self, domain):
        logger.debug('run parallel')
        
        status_gens = [child.run(domain) for child in self._children]
        statuses = [None] * len(self._children)
        leaf_nodes = [None] * len(self._children)
        leaf_statuses = [None] * len(self._children)
        
        n_successes = 0
        n_failures = 0

        succeeded = False
        should_break = False
        while True:
            for idx, status_gen in enumerate(status_gens):
                try:
                    leaf_node, leaf_status, status = next(status_gen)
                    statuses[idx] = status

                    leaf_nodes[idx] = leaf_node
                    leaf_statuses[idx] = leaf_status

                    if status == BTStatus.SUCCESS:
                        n_successes += 1

                    if status == BTStatus.FAILURE:
                        n_failures += 1
                except StopIteration:
                    pass

                if n_successes >= self._success_threshold:
                    succeeded = True
                    should_break = True
                    break

                if n_failures > len(self._children) - self._success_threshold:
                    should_break = True
                    break

            if should_break:
                break

            yield leaf_nodes, leaf_statuses, BTStatus.RUNNING

        if succeeded:
            logger.debug(f'{self} to yield success b/c {n_successes} successes')
            yield leaf_nodes, leaf_statuses, BTStatus.SUCCESS
        else:
            logger.debug(f'{self} to yield failure b/c {n_failures} failures')
            yield leaf_nodes, leaf_statuses, BTStatus.FAILURE

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label=f'=>{self._success_threshold}', shape='square')
        graph.add_node(this_node)

        for child in self._children:
            child_root_node, child_graph = child.get_dot_graph()
            merge_graphs(graph, child_graph)
            graph.add_edge(Edge(this_node, child_root_node))

        return this_node, graph


class NegationDecorator(BTNode):

    def __init__(self, child):
        super().__init__()
        self._child = child

    def run(self, domain):
        logger.debug('run negation')
        status_gen = self._child.run(domain)
        for leaf_node, leaf_status, status in status_gen:
            if status == BTStatus.RUNNING:
                logger.debug(f'{self} to yield running b/c {leaf_node} yielded running')
                yield leaf_node, leaf_status, BTStatus.RUNNING
            elif status == BTStatus.SUCCESS:
                logger.debug(f'{self} to yield failure b/c {leaf_node} yielded success')
                yield leaf_node, leaf_status, BTStatus.FAILURE
                break
            elif status == BTStatus.FAILURE:
                logger.debug(f'{self} to yield success b/c {leaf_node} yielded failure')
                yield leaf_node, leaf_status, BTStatus.SUCCESS
                break
            else:
                raise ValueError(f'Unknown status {status}')

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label='!=', shape='diamond')
        graph.add_node(this_node)

        child_root_node, child_graph = self._child.get_dot_graph()
        merge_graphs(graph, child_graph)
        graph.add_edge(Edge(this_node, child_root_node))

        return this_node, graph


class ConditionNode(BTNode):

    @abstractmethod
    def _eval(self, state: State) -> bool:
        pass

    def run(self, domain):
        logger.debug(f'run condition {self.__class__.__name__}')
        while True:
            if self._eval(domain.state):
                logger.debug(f'{self} to yield success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
            else:
                logger.debug(f'{self} to yield failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
            break

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label=self.__class__.__name__, shape='ellipse')
        graph.add_node(this_node)

        return this_node, graph


class SkillNode(BTNode):

    def __init__(self, skill_name, skill_param):
        super().__init__()
        self._skill_name = skill_name
        self._skill_param = skill_param

    def run(self, domain):        
        if self._skill_name == 'record_trajectory' and 'skill_duration' in self.blackboard.keys():
            self._skill_param['duration'] = float(self.blackboard['skill_duration'])
        elif self._skill_name == 'reset_arm':
            self._skill_param['goal_joints'] = [0, -math.pi / 4, 0, -3 * math.pi / 4, 0, math.pi / 2, math.pi / 4]
            self._skill_name = 'one_step_joint'
        elif self._skill_name == 'go_to_start' and 'skill_name' in self.blackboard.keys():
            self._skill_param['goal_joints'] = list(self.blackboard[self.blackboard['skill_name']]['trajectory']['skill_state_dict']['q'][0])
            self._skill_name = 'one_step_joint'
        elif self._skill_name == 'one_step_pose':
            if not isinstance(self._skill_param['goal_pose'], list):
                self._skill_param['goal_pose'] = self.blackboard['goal_poses'][self._skill_param['goal_pose']]
        elif self._skill_name == 'replay_trajectory' and 'skill_name' in self.blackboard.keys():
            self._skill_param['traj'] = self.blackboard[self.blackboard['skill_name']]['trajectory']['skill_state_dict']['q'].tolist()
            self._skill_name = 'stream_joint_traj'
        elif self._skill_name == 'execute_dmp_trajectory' and 'skill_name' in self.blackboard.keys():
            if self.blackboard[self.blackboard['skill_name']]['dmp_params']['dmp_type'] == 0:
                self._skill_param = {
                    'duration' : 5,
                    'dt' : 0.01,
                    'position_dmp_params' : self.blackboard[self.blackboard['skill_name']]['dmp_params'],
                    'quat_dmp_params' : self.blackboard[self.blackboard['skill_name']]['dmp_params']['quat_dmp_params']
                }
                self._skill_name = 'one_step_quat_pose_dmp'
            else:
                self._skill_param = {
                    'duration' : 5,
                    'dt' : 0.01,
                    'dmp_params' : self.blackboard[self.blackboard['skill_name']]['dmp_params']
                }
                self._skill_name = 'one_step_joint_dmp'

        self.blackboard['skill_id'] = domain.run_skill(self._skill_name, json.dumps(self._skill_param))
        
        logger.debug(f'{self} running skill with {self._skill_name} on {self.blackboard["skill_id"]}')
        while True:
            skill_status = domain.get_skill_status(self.blackboard['skill_id'])
            if skill_status in ('running', 'registered'):
                logger.debug(f'{self} to yield running')
                yield self, BTStatus.RUNNING, BTStatus.RUNNING
            elif skill_status == 'success':
                logger.debug(f'{self} to yield success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
                break
            elif skill_status == 'failure':
                logger.debug(f'{self} to yield failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
                break
            else:
                raise ValueError(f'Unknown status {skill_status}')

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        this_node = Node(self._uuid_str, label=self._skill_name, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class ResolveQueryNode(BTNode):

    def __init__(self, query_name, query_param):
        super().__init__()
        self._query_name = query_name
        self._query_param = query_param

    def run(self, domain):
        logger.debug(f'{self} running resolving query {self._query_name} with query name: {self._query_name}')  
        while True:
            query_status = 'success'

            query_response = {}
            has_buttons = ('buttons' in self._query_param.keys())
            has_sliders = ('sliders' in self._query_param.keys())
            has_text_inputs = ('text_inputs' in self._query_param.keys())
            has_dmp_params = ('bokeh_display_type' in self._query_param.keys() and self._query_param['bokeh_display_type'] == 0)
            label_image = ('bokeh_display_type' in self._query_param.keys() and self._query_param['bokeh_display_type'] == 1)
            has_points = ('bokeh_display_type' in self._query_param.keys() and self._query_param['bokeh_display_type'] == 2)

            query_complete = True

            if has_buttons:
                button_inputs = domain.get_memory_objects(['buttons'])['buttons']
                for button in self._query_param['buttons']:
                    if button['name'] not in button_inputs.keys():
                        query_complete = False
                        continue
                query_response['button_inputs'] = button_inputs
            if has_sliders:
                sliders = domain.get_memory_objects(['sliders'])['sliders']
                for slider in self._query_param['sliders']:
                    if slider['name'] not in sliders.keys():
                        query_complete = False
                        continue
                query_response['sliders'] = sliders
            if has_text_inputs:
                text_inputs = domain.get_memory_objects(['text_inputs'])['text_inputs']
                for text_input in self._query_param['text_inputs']:
                    if text_input['name'] not in text_inputs.keys():
                        query_complete = False
                        continue
                query_response['text_inputs'] = text_inputs
            if has_dmp_params:
                dmp_info = domain.get_memory_objects(['dmp_params'])['dmp_params']
                dmp_params = {}
                quat_dmp_params = {}
                dmp_params['dmp_type'] = dmp_info.dmp_type
                dmp_params['tau'] = dmp_info.tau
                dmp_params['alpha'] = dmp_info.alpha
                dmp_params['beta'] = dmp_info.beta
                dmp_params['num_dims'] = dmp_info.num_dims
                dmp_params['num_basis'] = dmp_info.num_basis
                dmp_params['num_sensors'] = dmp_info.num_sensors
                dmp_params['mu'] = dmp_info.mu
                dmp_params['h'] = dmp_info.h
                dmp_params['phi_j'] = dmp_info.phi_j
                dmp_params['weights'] = np.array(dmp_info.weights).reshape((dmp_info.num_dims,dmp_info.num_sensors,dmp_info.num_basis)).tolist()
                if dmp_info.dmp_type == 0:
                    quat_dmp_params['tau'] = dmp_info.quat_tau
                    quat_dmp_params['alpha'] = dmp_info.quat_alpha
                    quat_dmp_params['beta'] = dmp_info.quat_beta
                    quat_dmp_params['num_dims'] = dmp_info.quat_num_dims
                    quat_dmp_params['num_basis'] = dmp_info.quat_num_basis
                    quat_dmp_params['num_sensors'] = dmp_info.quat_num_sensors
                    quat_dmp_params['mu'] = dmp_info.quat_mu
                    quat_dmp_params['h'] = dmp_info.quat_h
                    quat_dmp_params['phi_j'] = dmp_info.quat_phi_j
                    quat_dmp_params['weights'] = np.array(dmp_info.quat_weights).reshape((dmp_info.quat_num_dims,dmp_info.quat_num_sensors,dmp_info.quat_num_basis)).tolist()
                    dmp_params['quat_dmp_params'] = quat_dmp_params
                query_response['dmp_params'] = dmp_params
            if label_image:
                query_response = domain.get_memory_objects(['request_next_image', 'object_names', 'masks', 'bounding_boxes'])
                query_response['button_inputs'] = {'request_next_image': query_response['request_next_image']}
            if has_points:
                query_response = domain.get_memory_objects(['object_names', 'desired_positions'])

            if not query_complete:
                query_status = 'running'
            else:
                self.blackboard['query_response'] = query_response
                domain.clear_human_inputs()

            if query_status == 'running':
                logger.debug(f'{self} to yield running')
                yield self, BTStatus.RUNNING, BTStatus.RUNNING
            elif query_status == 'success':
                logger.debug(f'{self} to yield success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
                break
            elif query_status == 'failure':
                logger.debug(f'{self} to yield failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
                break
            else:
                raise ValueError(f'Unknown status {query_status}')

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label='Resolve Query', shape='box')
        graph.add_node(this_node)

        return this_node, graph


class QueryNode(BTNode):

    def __init__(self, query_name, query_param):
        super().__init__()
        self._query_name = query_name
        self._query_param = query_param

    def run(self, domain):
        if 'display_type' in self._query_param.keys() and self._query_param['display_type'] == 2:
            self._query_param['traj1'] = list(self.blackboard['recorded_trajectory']['skill_state_dict']['q'].flatten())
        elif 'display_type' in self._query_param.keys() and self._query_param['display_type'] == 3:
            if self._query_param['bokeh_display_type'] == 0:
                bokeh_traj = {}
                bokeh_traj['time_since_skill_started'] = list(self.blackboard['recorded_trajectory']['skill_state_dict']['time_since_skill_started'])
                bokeh_traj['num_joints'] = 7
                bokeh_traj['cart_traj'] = list(np.array(self.blackboard['recorded_trajectory']['skill_state_dict']['O_T_EE']).flatten())
                bokeh_traj['joint_traj'] = list(self.blackboard['recorded_trajectory']['skill_state_dict']['q'].flatten())
                self._query_param['bokeh_traj'] = bokeh_traj
            elif self._query_param['bokeh_display_type'] == 1 or self._query_param['bokeh_display_type'] == 2:
                self._query_param['bokeh_image'] = self.blackboard['image'].tolist()
        
        self.blackboard['query_id'] = domain.run_query(self._query_name, json.dumps(self._query_param))
        logger.debug(f'{self} running query {self._query_name} with id: {self.blackboard["query_id"]}') 
        while True:
            query_status = domain.get_query_status(self.blackboard['query_id'])
            if query_status in ('running', 'registered'):
                logger.debug(f'{self} to yield running')
                yield self, BTStatus.RUNNING, BTStatus.RUNNING
            elif query_status == 'success':
                logger.debug(f'{self} to yield success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
                break
            elif query_status == 'failure':
                logger.debug(f'{self} to yield failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
                break
            elif query_status == 'cancelled':
                logger.debug(f'{self} to yield cancelled')
                yield self, BTStatus.RUNNING, BTStatus.RUNNING
                break
            else:
                raise ValueError(f'Unknown status {query_status}')

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'RunQuery-'+self._query_name

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class GenerateDepthImagePathNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):
        rgb_image_path = self.blackboard['image_path']
        self.blackboard['depth_image_path'] = rgb_image_path[:rgb_image_path.rfind('/')+1] + 'depth_' + rgb_image_path[rgb_image_path.rfind('/')+1:]
        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Generate Depth Image Path'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class GenerateGoalPointsNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):
        (goal_points_success, goal_points) = domain.get_goal_points(self.blackboard['depth_image_path'], self.blackboard['desired_positions'])
        if goal_points_success:
            self.blackboard['goal_points'] = goal_points
            logger.debug(f'{self} to yield success')
            yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
        else: 
            logger.debug(f'{self} to yield failure')
            yield self, BTStatus.FAILURE, BTStatus.FAILURE

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Generate Goal Points'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class GeneratePickAndPlacePositionsNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):

        goal_pose_1 = self.blackboard['goal_points'][0]
        goal_pose_1.y -= 0.04
        intermediate_height_offset = 0.11
        tong_height = 0.22
        intermediate_pose = RigidTransform(rotation=np.array([
            [1, 0, 0],
            [0, -1, 0],
            [0, 0, -1],
        ]), translation=np.array([goal_pose_1.x, goal_pose_1.y, tong_height+intermediate_height_offset]))

        grasp_pose = RigidTransform(rotation=np.array([
            [1, 0, 0],
            [0, -1, 0],
            [0, 0, -1],
        ]), translation=np.array([goal_pose_1.x, goal_pose_1.y, tong_height]))

        self.blackboard['goal_poses'] = { 'intermediate' : list(convert_rigid_transform_to_array(intermediate_pose)),
                                          'grasp' : list(convert_rigid_transform_to_array(grasp_pose))
                                        }

        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Generate Pick and Place Positions'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class SaveImageNode(BTNode):

    def __init__(self, camera_topic_name, camera_type, save_image_path_flag, use_saved_image_path_flag):
        super().__init__()
        self._camera_topic_name = camera_topic_name
        self._camera_type = camera_type
        self._save_image_path_flag = save_image_path_flag
        self._use_saved_image_path_flag = use_saved_image_path_flag

    def run(self, domain):
        if self._camera_type == 'rgb':
            (image_request_success, image_path) = domain.save_rgb_camera_image(self._camera_topic_name)
        elif self._camera_type == 'depth':
            if self._use_saved_image_path_flag:
                (image_request_success, image_path) = domain.save_depth_camera_image(self._camera_topic_name, self.blackboard['depth_image_path'])

        while True:
            if image_request_success:
                if self._save_image_path_flag:
                    self.blackboard['image_path'] = image_path
                logger.debug(f'{self} to yield success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
            else: 
                logger.debug(f'{self} to yield failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
            break

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'save_rgb_camera_image-'+self._camera_topic_name

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class SaveMasksNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):

        (request_success, image_path) = domain.save_image_labels(self.blackboard['image_path'], self.blackboard['query_response']['object_names'], self.blackboard['query_response']['masks'], self.blackboard['query_response']['bounding_boxes'])
        while True:
            if request_success:
                self.blackboard['image_path'] = image_path
                logger.debug(f'{self} to yield success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
            else: 
                logger.debug(f'{self} to yield failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
            break

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Save Image Masks'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class SaveTextInputToBlackBoardNode(BTNode):

    def __init__(self, text_input_name, blackboard_key):
        super().__init__()
        self._text_input_name = text_input_name
        self._blackboard_key = blackboard_key 

    def run(self, domain):

        self.blackboard[self._blackboard_key] = self.blackboard['query_response']['text_inputs'][self._text_input_name]
        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Save ' + self._text_input_name + ' To Blackboard'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class SaveQueryItemToBlackBoardNode(BTNode):

    def __init__(self, query_item_name, blackboard_key):
        super().__init__()
        self._query_item_name = query_item_name
        self._blackboard_key = blackboard_key 

    def run(self, domain):

        self.blackboard[self._blackboard_key] = self.blackboard['query_response'][self._query_item_name]
        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Save ' + self._query_item_name + ' To Blackboard'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class SaveTrajectoryInfoToMemoryNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):
        self.blackboard['recorded_trajectory']['duration'] = self.blackboard['skill_duration']
        domain.set_memory_objects({self.blackboard['skill_name'] : {'trajectory' : self.blackboard['recorded_trajectory'], 
                                                                    'dmp_params' : self.blackboard['query_response']['dmp_params']}})
        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Save Trajectory Info To Memory'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class SaveMemoryToBlackBoardNode(BTNode):

    def __init__(self, memory_name, blackboard_key):
        super().__init__()
        self._memory_name = memory_name
        self._blackboard_key = blackboard_key 

    def run(self, domain):

        if self._memory_name[0] == '<' and self._memory_name[-1] == '>':
            self._memory_name = self.blackboard[self._memory_name[1:-1]]
        if self._blackboard_key[0] == '<' and self._blackboard_key[-1] == '>':
            self._blackboard_key = self.blackboard[self._blackboard_key[1:-1]]

        self.blackboard[self._blackboard_key] = domain.get_memory_objects([self._memory_name])[self._memory_name]
        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Save ' + self._memory_name + ' To Blackboard'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class ClearMemoryNode(BTNode):

    def __init__(self, memory_name):
        super().__init__()
        self._memory_name = memory_name

    def run(self, domain):

        domain.clear_memory([self._memory_name])
        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Clear ' + self._memory_name + ' From Memory'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class ClearBlackBoardNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):

        self.blackboard = {}
        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Clear Blackboard'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class CancelSkillNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):

        if domain.get_skill_status(self.blackboard['skill_id']) == 'running':
            domain.cancel_skill(self.blackboard['skill_id'])

        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Cancel_Skill'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class CancelQueryNode(BTNode):

    def __init__(self):
        super().__init__()

    def run(self, domain):

        if domain.get_query_status(self.blackboard['query_id']) == 'running':
            domain.cancel_query(self.blackboard['query_id'])

        logger.debug(f'{self} to yield success')
        yield self, BTStatus.SUCCESS, BTStatus.SUCCESS

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'Cancel_Query'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph

class GetImageNode(BTNode):

    def __init__(self, use_saved_image_path_flag):
        super().__init__()
        self._use_saved_image_path_flag = use_saved_image_path_flag

    def run(self, domain):
        if self._use_saved_image_path_flag:
            (image_request_success, image_path, image) = domain.get_rgb_image(self.blackboard['image_path'])
        else:
            (image_request_success, image_path, image) = domain.get_rgb_image()

        if image_request_success:
            self.blackboard['image'] = image
            self.blackboard['image_path'] = image_path
            logger.debug(f'{self} to yield success')
            yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
        else: 
            logger.debug(f'{self} to yield failure')
            yield self, BTStatus.FAILURE, BTStatus.FAILURE

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = 'get_rgb_image'

        this_node = Node(self._uuid_str, label=param_str, shape='box')
        graph.add_node(this_node)

        return this_node, graph


class SkillParamSelector(ABC):

    @abstractmethod
    def __call__(self, state: State) -> str:
        pass
