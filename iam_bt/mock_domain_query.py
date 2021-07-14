from abc import ABC, abstractmethod
from pillar_state import State

def human_interface_handler(data=None):
    return {
        'human:exec/all': True,
        'human:exec/reset': False,
        'human:exec/grasp': False,
        'human:exec/move_ee_to_pose': False,
        'human:exec/open_gripper': False,
    }

class BaseMockDomainClient(ABC):

    def __init__(self):
        self._state = self._make_init_state()

        self._skill_dict = {}
        self._next_skill_id = 0
        self._current_skill_id = -1

        self._query_skill_dict = {}
        self._next_query_skill_id = 0
        self._current_query_skill_id = -1

        self._tick_count = 0

    @abstractmethod
    def _make_init_state(self) -> State:
        pass

    def _mock_tick(self):
        pass

    @property
    def state(self):
        return self._state.copy()
    
    def run_skill(self, skill_name, param):
        skill_id = self._next_skill_id
        self._next_skill_id += 1

        self._skill_dict[skill_id] = {
            'skill_id': skill_id,
            'skill_name': skill_name,
            'param': param,
            'status': 'running',
            'start_tick': self._tick_count
        }
        self._current_skill_id = skill_id

        return skill_id

    def get_skill_status(self, skill_id):
        self._mock_tick()
        return self._skill_dict[skill_id]['status']
    
    def run_query_skill(self, query_skill_name, query_param):
        query_skill_id = self._next_query_skill_id
        self._next_query_skill_id += 1

        self._query_skill_dict[query_skill_id] = {
            'skill_id': query_skill_id,
            'skill_name': query_skill_name,
            'param': query_param,
            'status': 'running',
            'start_tick': self._tick_count
        }
        self._current_query_skill_id = query_skill_id

        return query_skill_id

    def get_query_skill_status(self, query_skill_id):
        self._mock_tick(is_query_skill=True)
        return self._query_skill_dict[query_skill_id]['status']


class MockPenInJarWithHumanQueryDomainClient(BaseMockDomainClient):

    def _make_init_state(self):
        state = State()
        state['frame:pen:pose/position'] = [0.1, 0, 0]
        for k,v in human_interface_handler().items():
            state[k] = v
        return state

    def _mock_tick(self, is_query_skill=False):
        self._tick_count += 1

        if not is_query_skill:
            skill_info = self._skill_dict[self._current_skill_id]
            skill_status = skill_info['status']
            skill_start_tick = skill_info['start_tick']
            skill_name = skill_info['skill_name']
            skill_id = skill_info['skill_id']
            
            if skill_status == 'running':
                if skill_name == 'reset':
                    if self._tick_count > skill_start_tick + 10:
                        self._skill_dict[skill_id]['status'] = 'success'
                elif skill_name == 'grasp':
                    if self._tick_count > skill_start_tick + 3:
                        self._skill_dict[skill_id]['status'] = 'success'
                        self._state['frame:pen:pose/position'] = [0.1, 0, 0.2]
                elif skill_name == 'move_ee_to_pose':
                    if self._tick_count > skill_start_tick + 4:
                        self._skill_dict[skill_id]['status'] = 'success'
                elif skill_name == 'open_gripper':
                    if self._tick_count > skill_start_tick + 2:
                        self._skill_dict[skill_id]['status'] = 'success'     
        else:
            skill_info = self._query_skill_dict[self._current_query_skill_id]
            skill_status = skill_info['status']
            skill_start_tick = skill_info['start_tick']
            skill_name = skill_info['skill_name']
            skill_id = skill_info['skill_id']
            
            if skill_status == 'running':
                if skill_name == 'toggle_button_reset':
                    if self._tick_count > skill_start_tick + 2:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/reset'] = True
                        # then every other status is false 
                        
                    if self._tick_count > skill_start_tick + 3:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/reset'] = False
                elif skill_name == 'toggle_button_grasp':
                    if self._tick_count > skill_start_tick + 3:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/grasp'] = True
                    if self._tick_count > skill_start_tick + 4:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/reset'] = False
                elif skill_name == 'toggle_button_move_ee_to_pose':
                    if self._tick_count > skill_start_tick + 2:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/move_ee_to_pose'] = True
                    if self._tick_count > skill_start_tick + 3:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/move_ee_to_pose'] = True
                elif skill_name == 'toggle_button_open_gripper':
                    if self._tick_count > skill_start_tick + 2:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/open_gripper'] = True 
                    if self._tick_count > skill_start_tick + 3:
                        self._query_skill_dict[skill_id]['status'] = 'success'
                        self._state['human:exec/open_gripper'] = False 
                elif skill_name == 'make_false_all':
                    # if self._tick_count > skill_start_tick + 5:
                    #     self._query_skill_dict[skill_id]['status'] = 'success' 
                    #     self._state['human:exec/all'] = True
                    if self._tick_count > skill_start_tick + 5:
                        self._query_skill_dict[skill_id]['status'] = 'success' 
                        self._state['human:exec/all'] = False


# class BaseMockQueryDomainClient(ABC):
#     def __init__(self):
#         # self._state_client = StateClient()
#         # self._robot_client = RobotClient()

#         self._state = self._make_init_state()

#     @property
#     def state(self):
#         return self._state_client.get_state()

#     def run_skill(self, skill_name, skill_param=''):
#         return self._robot_client.run_skill(skill_name, skill_param)

#     def get_skill_status(self, skill_id):
#         return self._robot_client.get_skill_status(skill_id)
    
#     # @abstractmethod
#     def _make_init_state(self):
#         state = State()
#         state['frame:pen:pose/position'] = [0.1, 0, 0]
#         for k,v in human_interface_handler().items():
#             state[k] = v
#         return state