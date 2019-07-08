import re
from rdflib import URIRef
from rdflib.namespace import DC, RDF, RDFS

import pytest

from rs_import._import import edm, m4p0
from tests import _TestDataSetImport


def test_valid_dataset(test_config, test_data):
    result = _TestDataSetImport(
        test_data / "valid_dataset_description", test_config
    ).run()

    graph_iri = result.value(
        predicate=RDF.type,
        object=URIRef("https://enter.museum4punkt0.de/ontology/RDFGraph"),
    )
    assert (graph_iri, RDF.type, m4p0.RDFGraph) in result
    assert re.match(
        r"https://öbjects\.museum4punkt0\.de/project_1/ "
        r"@ \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d",
        result.value(subject=graph_iri, predicate=RDFS.label).value,
    )

    assert (
        str(result.value(subject=graph_iri, predicate=DC.date).datatype)
        == "http://www.w3.org/2001/XMLSchema#dateTime"
    )
    assert (
        str(result.value(subject=graph_iri, predicate=edm.dataProvider))
        == "https://enter.museum4punkt0.de/resource/institution_1"
    )


def test_invalid_dataset(test_data, test_config):
    with pytest.raises(SystemExit):
        _TestDataSetImport(test_data / "invalid_dataset", test_config)


def test_invalid_dataset_description_1(test_config, test_data):
    with pytest.raises(SystemExit):
        _TestDataSetImport(
            test_data / "invalid_dataset_description_1", test_config
        ).run()
