from abc import ABC, abstractmethod
from typing import Tuple
from enum import Enum

from uuid import uuid4
from pydot import Dot, Edge, Node
from pillar_state import State

from .utils import merge_graphs


class BTStatus(Enum):
    RUNNING=0
    SUCCESS=1
    FAILURE=2


class BTNode(ABC):

    @abstractmethod
    def run(self, domain) -> BTStatus:
        pass

    @abstractmethod
    def get_dot_graph(self) -> Tuple[Node, Dot]:
        pass

    def save_graph_vis(self, save_path):
        _, graph = self.get_dot_graph()
        graph.write_png(save_path)

    def _create_dot_graph(self):
        return Dot('BT', graph_type='digraph', splines=False)


class FallBack(BTNode):

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

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(f'fallback_{uuid4()}', label='?', shape='square')
        graph.add_node(this_node)

        for child in self._children:
            child_root_node, child_graph = child.get_dot_graph()
            merge_graphs(graph, child_graph)
            graph.add_edge(Edge(this_node, child_root_node))

        return this_node, graph


class Sequence(BTNode):

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

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(f'sequence_{uuid4()}', label='->', shape='square')
        graph.add_node(this_node)

        for child in self._children:
            child_root_node, child_graph = child.get_dot_graph()
            merge_graphs(graph, child_graph)
            graph.add_edge(Edge(this_node, child_root_node))

        return this_node, graph


class NegationDecorator(BTNode):

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

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(f'negation_condition_{uuid4()}', label='!=', shape='diamond')
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
        print(f'run condition {self.__class__.__name__}')
        while True:
            if self._eval(domain.state):
                print('yield success')
                yield BTStatus.SUCCESS
            else:
                print('yield failure')
                yield BTStatus.FAILURE
            break

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(f'condition_{uuid4()}', label=self.__class__.__name__, shape='ellipse')
        graph.add_node(this_node)

        return this_node, graph


class SkillParamSelector(ABC):

    @abstractmethod
    def __call__(self, state: State) -> str:
        pass


class SkillNode(BTNode):

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

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = self._param_selector.__class__.__name__
        if param_str == 'function':
            param_str = ''

        this_node = Node(f'skill_{uuid4()}', label=f'{self._skill_name}({param_str})', shape='box')
        graph.add_node(this_node)

        return this_node, graph


def run_tree(tree, domain):
    status_gen = tree.run(domain)
    for status in status_gen:
        print('run tree', status)