from pillar_state import State


class MockBoxInCabinetDomainHandlerClient:

    def __init__(self):
        self._state = State()
        self._state['frame:cabinet:open'] = [False]
        self._state['frame:cabinet:handle:pose/position'] = [0.1, 0.1, 0.3]
        self._state['frame:box:pose/position'] = [0.1, 0, 0]

        self._skill_dict = {}
        self._next_skill_id = 0
        self._current_skill_id = -1

        self._tick_count = 0

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

    @property
    def current_skill_id(self):
        return self._current_skill_id

    @property
    def current_skill_info(self):
        return self._skill_dict[self.current_skill_id]

    def _mock_tick(self):
        self._tick_count += 1
        print(f'mock tick: {self._tick_count}')

        skill_info = self.current_skill_info
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

    def get_skill_exec_status(self, skill_id):
        self._mock_tick()
        return self._skill_dict[skill_id]['status']
    