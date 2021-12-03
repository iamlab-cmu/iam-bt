from abc import ABC, abstractmethod
from pillar_state import State


class BaseMockDomainClient(ABC):

    def __init__(self):
        self._state = self._make_init_state()

        self._skill_dict = {}
        self._next_skill_id = 0
        self._current_skill_id = -1

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


class MockBoxInCabinetDomainClient(BaseMockDomainClient):

    def _make_init_state(self):
        state = State()
        state['frame:cabinet:open'] = [False]
        state['frame:cabinet:handle:pose/position'] = [0.1, 0.1, 0.3]
        state['frame:box:pose/position'] = [0.1, 0, 0]
        return state

    def _mock_tick(self):
        self._tick_count += 1

        skill_info = self._skill_dict[self._current_skill_id]
        skill_status = skill_info['status']
        skill_start_tick = skill_info['start_tick']
        skill_name = skill_info['skill_name']
        skill_id = skill_info['skill_id']
        if skill_status == 'running':
            if skill_name == 'reset':
                if self._tick_count > skill_start_tick + 10:
                    self._skill_dict[skill_id]['status'] = 'success'
            elif skill_name == 'open':
                if self._tick_count > skill_start_tick + 5:
                    self._skill_dict[skill_id]['status'] = 'success'
                    self._state['frame:cabinet:open'] = [True]
            elif skill_name == 'grasp':
                if self._tick_count > skill_start_tick + 3:
                    self._skill_dict[skill_id]['status'] = 'success'
                    self._state['frame:box:pose/position'] = [0.1, 0, 0.2]
            elif skill_name == 'move_ee_to_pose':
                if self._tick_count > skill_start_tick + 4:
                    self._skill_dict[skill_id]['status'] = 'success'
            elif skill_name == 'open_gripper':
                if self._tick_count > skill_start_tick + 2:
                    self._skill_dict[skill_id]['status'] = 'success'        


class MockPenInJarDomainClient(BaseMockDomainClient):

    def _make_init_state(self):
        state = State()
        state['frame:pen:pose/position'] = [0.1, 0, 0]
        return state

    def _mock_tick(self):
        self._tick_count += 1

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
    

class MockPenInJarParallelDomainClient(BaseMockDomainClient):

    def _make_init_state(self):
        state = State()
        state['frame:pen:pose/position'] = [0.1, 0, 0]
        return state

    def _mock_tick(self):
        self._tick_count += 1

        for skill_id, skill_info in self._skill_dict.items():
            skill_status = skill_info['status']
            skill_start_tick = skill_info['start_tick']
            skill_name = skill_info['skill_name']
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
