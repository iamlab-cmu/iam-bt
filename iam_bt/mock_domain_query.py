import json
import numpy as np
from abc import ABC, abstractmethod
from pillar_state import State


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
    
    def run_query(self, query_name, query_param):
        query_skill_id = self._next_query_skill_id
        self._next_query_skill_id += 1

        self._query_skill_dict[query_skill_id] = {
            'skill_id': query_skill_id,
            'skill_name': '',
            'param': query_param,
            'status': 'running',
            'start_tick': self._tick_count,
            'click_this_button' : None,
        }
        self._current_query_skill_id = query_skill_id

        return query_skill_id

    def get_query_status(self, query_skill_id):
        self._mock_tick(is_query=True)
        return self._query_skill_dict[query_skill_id]['status']

          

class MockPenInJarWithQueryDomainClient(BaseMockDomainClient):

    def _make_init_state(self):
        state = State()
        state['frame:pen:pose/position'] = [0.1, 0, 0]
        state['clicked_button_index'] = [-1]
        return state
    
    def mock_process_human_interface_request(self, skill_info):
        
        skill_start_tick = skill_info['start_tick']
        params = skill_info['param']
        skill_id = skill_info['skill_id']
        button_clicked_idx = skill_info['click_this_button']

        if type(params) is str:
            params = json.loads(params)
        
        if "buttons" in params:
            buttons = params['buttons']
            if self._tick_count > 50:
                print(self._tick_count)
                self._query_skill_dict[skill_id]['status'] = 'success'
                self._state['clicked_button_index'] = [-1]
                return

            if button_clicked_idx is None:
                button_idx = np.random.choice(list(np.arange(len(buttons))))
                skill_info['click_this_button'] = button_idx
            else:
                button_idx = skill_info['click_this_button']
                
            if self._tick_count > skill_start_tick + 3:
                self._query_skill_dict[skill_id]['status'] = 'success'
                self._state['clicked_button_index'] = [button_idx]
                
        
    def _mock_tick(self, is_query=False):
        self._tick_count += 1

        if is_query:
            skill_info = self._query_skill_dict[self._current_query_skill_id]
            # print("query: ", self._tick_count)
            self.mock_process_human_interface_request(skill_info)
        else:
            # print("skill: ", self._tick_count)
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

