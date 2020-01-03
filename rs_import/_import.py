import csv
import uuid
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from pprint import pformat
from types import SimpleNamespace
from typing import Dict, Optional
from urllib.parse import quote as url_quote

import yaml
from cerberus import Validator  # type: ignore
from rdflib import Graph, Literal, Namespace, URIRef  # type: ignore
from rdflib.namespace import RDF, RDFS, XSD  # type: ignore

from rs_import.logging import log, set_file_log_handler
from rs_import.constants import WEB_URL_PATTERN


# TODO make that configurable
OBJECTS_NAMESPACE = "https://enter.museum4punkt0.de/resource/"


# URI namespaces

crm = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
crmdig = Namespace("http://www.ics.forth.gr/isl/rdfs/3D-COFORM_CRMdig.rdfs#")
dc = Namespace("http://purl.org/dc/elements/1.1/")
dcterms = Namespace("http://purl.org/dc/terms/")
edm = Namespace("http://www.europeana.eu/schemas/edm/")
m4p0 = Namespace("https://enter.museum4punkt0.de/ontology/")


# validation schemas

dataset_description_schema = {
    "file_namespace": {
        "type": "string",
        "required": True,
        "regex": WEB_URL_PATTERN + "/$",
    },
    "data_provider": {"type": "string", "required": True, "regex": WEB_URL_PATTERN},
    "digital_app": {"type": "string", "regex": WEB_URL_PATTERN},
}


def lower_case_file_extension(value):
    path = Path(value)
    return str(path.with_suffix(path.suffix.lower()))


coreset_description_schema = {
    "Dateiname": {
        "type": "string",
        "required": True,
        "coerce": lower_case_file_extension,
    },
    "Rechtehinweis": {
        "type": "string",
        "required": True,
        "excludes": ["Lizenz", "Lizenzgeber"],
    },
    "Lizenz": {
        "type": "string",
        "required": True,
        "excludes": "Rechtehinweis",
        "dependencies": "Lizenzgeber",
        "allowed": [
            f"https://creativecommons.org/licenses/{x}/4.0/"
            for x in ("by", "by-nd", "by-sa", "by-nc", "by-nc-sa", "by-nc-cd")
        ]
        + ["https://creativecommons.org/publicdomain/"],
    },
    "Lizenzgeber": {"type": "string"},
    "Bezugsentität": {"type": "string"},
    "URL": {"type": "string", "regex": WEB_URL_PATTERN},
}

video_audio_description_schema = {
    **coreset_description_schema,
    # TODO
}

_3d_description_schema = {
    **coreset_description_schema,
    # TODO
}


dataset_description_validator = Validator(dataset_description_schema)
coreset_validator = Validator(coreset_description_schema)


class NamedGraphBackup(AbstractContextManager):
    def __init__(self):
        raise NotImplementedError

    def __enter__(self):
        raise NotImplementedError

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise NotImplementedError
        else:
            raise NotImplementedError


class DataSetImport:
    def __init__(self, path: Path, config: SimpleNamespace):
        log.info(f"Setting up import from {path}")

        self.config = config
        self.import_time = datetime.now()
        self.import_time_string = self.import_time.isoformat(timespec="seconds")

        log_folder = path / "logs"
        try:
            log_folder.mkdir(exist_ok=True)
        except FileNotFoundError:
            log.error(f"The import folder '{path}' doesn't exist. Aborting.")
            raise SystemExit(1)
        set_file_log_handler(log_folder / f"{self.import_time_string}.log")

        self.dataset_description = yaml.load(
            (path / "dataset.yml").read_text(), Loader=yaml.SafeLoader
        )

        self.source_files: Dict[str, Path] = {}
        for name in ("images", "audio_video", "3d", "entities"):
            data_file_path = path / f"{name}.csv"
            if data_file_path.exists():
                self.source_files[name] = data_file_path
        if not any(x in self.source_files for x in ("images", "audio_video", "3d")):
            log.error(
                "At least one of 'images.csv', 'audio_video.csv' or '3d.csv' "
                "must be present in an import folder."
            )
            raise SystemExit(1)

        self.graph: Optional[Graph] = None
        self.digital_app_creation: Optional[URIRef] = None

    def run(self):
        # generate triples from the various sources
        self.process_dataset_description()
        self.process_images_data()
        self.process_audio_video_data()
        self.process_3d_data()
        self.process_entities_data()

        self.submit()

    def submit(self):
        # submit the triples to the SPARQL-endpoint
        with NamedGraphBackup():
            log.info("# Submitting graph data via SPARQL.")
            raise NotImplementedError

    # input data processing

    def process_dataset_description(self):
        log.info("# Processing dataset description.")
        input_data = self.dataset_description

        log.debug(f"Input data: {input_data}")
        if not dataset_description_validator(input_data):
            log.error(
                "The dataset description document did not validate. These errors were "
                "reported:"
            )
            log.error(pformat(dataset_description_validator.errors))
            raise SystemExit(1)
        log.debug("Input data validated.")

        self.data_provider = URIRef(input_data["data_provider"])
        self.file_namespace = file_namespace = input_data["file_namespace"]

        # initialize graph
        self.graph_uuid = uuid.uuid5(uuid.NAMESPACE_URL, file_namespace)
        graph_iri = f"{OBJECTS_NAMESPACE}{self.graph_uuid}"
        graph = self.graph = Graph(identifier=graph_iri)

        # describe graph
        s = URIRef(graph_iri)
        for p, o in [
            (RDF.type, m4p0.RDFGraph),
            (RDFS.label, Literal(f"{file_namespace} @ {self.import_time_string}")),
            (edm.dataProvider, self.data_provider),
            (dc.date, Literal(self.import_time)),
        ]:
            graph.add((s, p, o))

        # TODO mind the 'digital_app' at a later stage

    def process_images_data(self):
        if self.source_files.get("images") is None:
            log.debug("No images' metadata found.")
            return
        log.info("# Processing images' metadata.")

        creation_uuid_ns = uuid.uuid5(uuid.NAMESPACE_URL, self.file_namespace)
        encountered_filenames = set()
        graph = self.graph

        with self.source_files["images"].open("rt", newline="") as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:

                normalized_row = {}
                # remove * indicator and drop empty fields
                for name, value in row.items():
                    if not value.strip():
                        continue
                    if name.endswith("*"):
                        name = name[:-1]
                    normalized_row[name] = value

                object_data = coreset_validator.validated(normalized_row)
                filename = object_data.get("Dateiname", "<missing>")
                if coreset_validator.errors:
                    log.error(
                        "An image metadata set did not validate. These errors "
                        f"were reported for the file {filename}:"
                    )
                    log.error(pformat(coreset_validator.errors))

                # TODO check URL if configured

                if filename in encountered_filenames:
                    log.error(f"Encountered redundant filename: {filename}")
                    log.critical("Aborting")
                    raise SystemExit(1)
                encountered_filenames.add(filename)

                s = URIRef(self.file_namespace + url_quote(filename))
                media_type = self.config.media_types[Path(filename).suffix[1:]]
                creation_uuid = uuid.uuid5(creation_uuid_ns, media_type)
                creation_iri = URIRef(f"{OBJECTS_NAMESPACE}{creation_uuid}")

                # TODO collect creation_iris and generate triples about them

                for p, o in [
                    (RDF.type, crmdig["D1.Digital_Object"]),
                    (m4p0.fileName, Literal(filename)),
                    (edm.dataProvider, self.data_provider),
                    (m4p0.hasMediaType, URIRef(media_type)),
                    (crm.P94i_was_created_by, creation_iri,),
                ]:
                    graph.add((s, p, o))

                if "Rechtehinweis" in object_data:
                    graph.add((s, dc.rights, Literal(object_data["Rechtehinweis"])))
                elif "Lizenz" in object_data:
                    graph.add((s, dcterms.license, URIRef(object_data["Lizenz"])))
                    graph.add((s, m4p0.licensor, Literal(object_data["Lizenzgeber"])))
                else:
                    raise AssertionError

                if "Bezugsentität" in object_data:
                    related_iri = OBJECTS_NAMESPACE + str(
                        uuid.uuid5(self.graph_uuid, object_data["Bezugsentität"])
                    )
                    graph.add((s, m4p0.refersToMuseumObject, URIRef(related_iri)))

                if "URL" in object_data:
                    graph.add(
                        (
                            s,
                            edm.shownAt,
                            Literal(object_data["url"], datatype=XSD.anyURI),
                        )
                    )

    def process_audio_video_data(self):
        if self.source_files.get("audio_video") is None:
            log.debug("No audios' metadata found.")
            return
        log.info("# Processing audios' metadata")

    def process_3d_data(self):
        if self.source_files.get("3d") is None:
            log.debug("No 3D objects' metadata found.")
            return
        log.info("# Processing 3D objects' metadata.")

    def process_entities_data(self):
        if self.source_files.get("objects") is None:
            log.debug("No entities' metadata found.")
            return
        log.info("# Processing entities' metadata.")
