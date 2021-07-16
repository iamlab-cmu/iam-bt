from .bt_status import BTStatus
from shortuuid import uuid

def merge_graphs(base_graph, new_graph):
    for node in new_graph.get_nodes():
        base_graph.add_node(node)
    for edge in new_graph.get_edges():
        base_graph.add_edge(edge)

    return base_graph


def run_tree(tree, domain, save_dir=None):
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)
        _, graph = tree.get_dot_graph()

    status_gen = tree.run(domain)
    tick = 0
    for leaf_bt_node, leaf_status, _ in status_gen:
        tick += 1

        if save_dir is not None:
            leaf_dot_node = graph.get_node(leaf_bt_node.uuid_str)[0]
            if leaf_status == BTStatus.RUNNING:
                leaf_dot_node.set_color('goldenrod4')
            elif leaf_status == BTStatus.SUCCESS:
                leaf_dot_node.set_color('green')
            elif leaf_status == BTStatus.FAILURE:
                leaf_dot_node.set_color('red')
            
            img_path = save_dir / f'{tick:010d}.png'
            graph.write_png(img_path)         

            leaf_dot_node.set_color('black')

def assign_unique_name(param_dict):
    '''
    
    '''
    for k,v in param_dict.items():
        if type(v) is list:
            new_v = []
            for vi in v:
                if type(vi) is not dict:
                    continue
                if 'name' in vi:
                    vi['name'] = '{}_{}'.format(vi['name'], uuid())
                new_v.append(vi)
                
            param_dict[k] = new_v
            
    return param_dict