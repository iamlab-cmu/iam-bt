from abc import ABC, abstractmethod
from typing import Tuple, Generator
import logging

from shortuuid import uuid
from pydot import Dot, Edge, Node
from pillar_state import State

from .bt_status import BTStatus
from .utils import merge_graphs


logger = logging.getLogger(__name__)


class BTNode(ABC):

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


class FallBack(BTNode):

    def __init__(self, children):
        super().__init__()
        assert len(children) > 0
        self._children = children

    def run(self, domain):
        logger.debug(f'run fallback')

        any_child_success = False
        for child in self._children:
            status_gen = child.run(domain)
            success = False
            for leaf_node, leaf_status, status in status_gen:
                if status == BTStatus.RUNNING:
                    logger.debug(f'fallback yield running')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    logger.debug(f'fallback yield success')
                    success = True
                    yield leaf_node, leaf_status, BTStatus.SUCCESS
                    break
                elif status == BTStatus.FAILURE:
                    logger.debug(f'fallback failed, moving on')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if success:
                any_child_success = True
                break

        if not any_child_success:
            logger.debug(f'fallback yield failure')
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
                    logger.debug(f'sequence running')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                elif status == BTStatus.SUCCESS:
                    logger.debug(f'sequence success, moving on')
                    yield leaf_node, leaf_status, BTStatus.RUNNING
                    break
                elif status == BTStatus.FAILURE:
                    logger.debug(f'sequence failure')
                    failure = True
                    yield leaf_node, leaf_status, BTStatus.FAILURE
                    break
                else:
                    raise ValueError(f'Unknown status {status}')

            if failure:
                any_child_failure = True
                break

        if not any_child_failure:
            logger.debug(f'sequence success')
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


class NegationDecorator(BTNode):

    def __init__(self, child):
        super().__init__()
        self._child = child

    def run(self, domain):
        logger.debug('run negation')
        status_gen = self._child.run(domain)
        for leaf_node, leaf_status, status in status_gen:
            if status == BTStatus.RUNNING:
                logger.debug('negation yield running')
                yield leaf_node, leaf_status, BTStatus.RUNNING
            elif status == BTStatus.SUCCESS:
                logger.debug('negation yield failure (got success)')
                yield leaf_node, leaf_status, BTStatus.FAILURE
                break
            elif status == BTStatus.FAILURE:
                logger.debug('negation yield success (got success)')
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
                logger.debug('yield success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
            else:
                logger.debug('yield failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
            break

    def get_dot_graph(self):
        graph = self._create_dot_graph()
        this_node = Node(self._uuid_str, label=self.__class__.__name__, shape='ellipse')
        graph.add_node(this_node)

        return this_node, graph


class SkillNode(BTNode):

    def __init__(self, skill_name, param_selector=None):
        super().__init__()
        self._skill_name = skill_name

        if param_selector is None:
            self._param_selector = lambda _ : ''
        else:
            self._param_selector = param_selector

    def run(self, domain):
        param = self._param_selector(domain.state)
        skill_id = domain.run_skill(self._skill_name, param)
        
        logger.debug(f'running skill with {self._skill_name} on {skill_id}')
        while True:
            skill_exec_status = domain.get_skill_exec_status(skill_id)
            if skill_exec_status == 'running':
                logger.debug('skill running')
                yield self, BTStatus.RUNNING, BTStatus.RUNNING
            elif skill_exec_status == 'success':
                logger.debug('skill success')
                yield self, BTStatus.SUCCESS, BTStatus.SUCCESS
                break
            elif skill_exec_status == 'failure':
                logger.debug('skill failure')
                yield self, BTStatus.FAILURE, BTStatus.FAILURE
                break
            else:
                raise ValueError(f'Unknown status {skill_exec_status}')

    def get_dot_graph(self):
        graph = self._create_dot_graph()

        param_str = self._param_selector.__class__.__name__
        if param_str == 'function':
            param_str = ''

        this_node = Node(self._uuid_str, label=f'{self._skill_name}({param_str})', shape='box')
        graph.add_node(this_node)

        return this_node, graph


class SkillParamSelector(ABC):

    @abstractmethod
    def __call__(self, state: State) -> str:
        pass
