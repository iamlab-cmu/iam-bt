from abc import ABC, abstractmethod
from enum import Enum

from pillar_state import State


class BTStatus(Enum):
    RUNNING=0
    SUCCESS=1
    FAILURE=2


class FallBack:

    def __init__(self, children):
        self._children = children

    def run(self, domain):
        print(f'run fallback')

        any_child_success = False
        for child in self._children:
            status_gen = child.run(domain)
            success = False
            for status in status_gen:
                if status == BTStatus.RUNNING:
                    print(f'fallback yield running')
                    yield BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    print(f'fallback yield success')
                    yield BTStatus.SUCCESS
                    success = True
                    break
                elif status == BTStatus.FAILURE:
                    print(f'fallback failed, moving on')
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if success:
                any_child_success = True
                break

        if not any_child_success:
            print(f'fallback yield failure')
            yield BTStatus.FAILURE


class Sequence:

    def __init__(self, children):
        self._children = children

    def run(self, domain):
        print('run sequence')
        
        any_child_failure = False
        for child in self._children:
            status_gen = child.run(domain)
            failure = False
            for status in status_gen:
                if status == BTStatus.RUNNING:
                    print(f'sequence running')
                    yield BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    print(f'sequence success, moving on')
                    break
                elif status == BTStatus.FAILURE:
                    print(f'sequence failure')
                    yield BTStatus.FAILURE
                    failure = True
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if failure:
                any_child_failure = True
                break

        if not any_child_failure:
            print(f'sequence success')
            yield BTStatus.SUCCESS


class NegationDecorator:

    def __init__(self, child):
        self._child = child

    def run(self, domain):
        print('run negation')
        status_gen = self._child.run(domain)
        for status in status_gen:
            if status == BTStatus.RUNNING:
                print('negation yield running')
                yield BTStatus.RUNNING
            elif status == BTStatus.SUCCESS:
                print('negation yield failure (got success)')
                yield BTStatus.FAILURE
                break
            elif status == BTStatus.FAILURE:
                print('negation yield success (got success)')
                yield BTStatus.SUCCESS
                break
            else:
                raise ValueError(f'Unknown status {status}')


class ConditionNode(ABC):

    @abstractmethod
    def _eval(self, state: State) -> bool:
        pass

    def run(self, domain):
        print(f'run condition {self.__class__.__name__}')
        while True:
            if self._eval(domain.state):
                print('yield success')
                yield BTStatus.SUCCESS
            else:
                print('yield failure')
                yield BTStatus.FAILURE
            break


class SkillParamSelector(ABC):

    @abstractmethod
    def __call__(self, state: State) -> str:
        pass


class SkillNode:

    def __init__(self, skill_name, param_selector=None):
        self._skill_name = skill_name

        if param_selector is None:
            self._param_selector = lambda _ : ''
        else:
            self._param_selector = param_selector

    def run(self, domain):
        param = self._param_selector(domain.state)
        skill_id = domain.run_skill(self._skill_name, param)
        
        print(f'running skill with {self._skill_name} on {skill_id}')
        while True:
            skill_exec_status = domain.get_skill_exec_status(skill_id)
            if skill_exec_status == 'running':
                print('skill running')
                yield BTStatus.RUNNING
            elif skill_exec_status == 'success':
                print('skill success')
                yield BTStatus.SUCCESS
                break
            elif skill_exec_status == 'failure':
                print('skill failure')
                yield BTStatus.FAILURE
                break
            else:
                raise ValueError(f'Unknown status {skill_exec_status}')


def run_tree(tree, domain):
    status_gen = tree.run(domain)
    for status in status_gen:
        print('run tree', status)