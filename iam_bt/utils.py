def merge_graphs(base_graph, new_graph):
    for node in new_graph.get_nodes():
        base_graph.add_node(node)
    for edge in new_graph.get_edges():
        base_graph.add_edge(edge)

    return base_graph