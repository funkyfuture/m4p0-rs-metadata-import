from rdflib import Graph

from rs_import._import import DataSetImport


class _TestDataSetImport(DataSetImport):
    """ A derived class of an import that stores the resulting graph as `_result`
        property. De-/serialization is applied as an intermediate step to validate
        the graph data structurally.
    """

    def run(self):
        super().run()
        return self._result

    def submit(self):
        serialized_graph = self.graph.serialize()
        parsed_graph = Graph()
        parsed_graph.parse(data=serialized_graph)
        self._result = parsed_graph
