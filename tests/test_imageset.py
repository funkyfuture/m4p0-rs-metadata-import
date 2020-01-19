import json

from rdflib import Namespace, URIRef
from rdflib.namespace import RDF

from tests import _TestDataSetImport


crmdig = Namespace("http://www.ics.forth.gr/isl/rdfs/3D-COFORM_CRMdig.rdfs#")
m4p0 = Namespace("https://enter.museum4punkt0.de/ontology/")


def test_imagset_and_entities(test_config, test_data):
    result = _TestDataSetImport(test_data / "valid_imageset", test_config).run()

    digital_objects = list(result.subjects(RDF.type, crmdig["D1.Digital_Object"]))
    assert len(digital_objects) == len(set(digital_objects)) == 18

    do_filenames = list(result.subjects(predicate=m4p0.fileName))
    assert len(do_filenames) == len(set(do_filenames)) == 18

    assert all(
        o == URIRef("https://www.iana.org/assignments/media-types/image/tiff")
        for o in result.objects(predicate=m4p0.hasMediaType)
    )

    assert all(
        isinstance(json.loads(x), dict) for x in result.objects(None, m4p0.jsonData)
    )

    assert len(result) == 8 + 18 * 7 + 12 * 6
