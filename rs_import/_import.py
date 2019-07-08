import uuid
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from pprint import pformat
from types import SimpleNamespace
from typing import Dict, Optional

import yaml
from cerberus import Validator  # type: ignore
from rdflib import Graph, Literal, Namespace, URIRef  # type: ignore
from rdflib.namespace import DC, RDF, RDFS  # type: ignore

from rs_import.logging import log, set_file_log_handler


# TODO make that configurable
OBJECTS_NAMESPACE = "https://enter.museum4punkt0.de/resource/"

URL_PATTERN = "^https?://.*"


# URI namespaces

edm = Namespace("http://www.europeana.eu/schemas/edm/")
m4p0 = Namespace("https://enter.museum4punkt0.de/ontology/")


# validation schemas

dataset_description_schema = {
    "file_namespace": {"type": "string", "required": True, "regex": URL_PATTERN + "/$"},
    "data_provider": {"type": "string", "required": True, "regex": URL_PATTERN},
    "digital_app": {"type": "string", "regex": URL_PATTERN},
}


validator = Validator()


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

        log.info(f"Setting up import from {path}")

        with (path / "dataset.yml").open("rt") as f:
            self.dataset_description = yaml.load(f, Loader=yaml.SafeLoader)

        self.source_files: Dict[str, Path] = {}
        for name in ("images", "audio_video", "3d", "entities"):
            if (path / f"{name}.csv").exists():
                self.source_files[name] = path / f"{name}.csv"
        if not any(x in self.source_files for x in ("images", "audio_video", "3d")):
            log.error(
                "At least one of 'images.csv', 'audio_video.csv' or '3d.csv' "
                "must be present in an import folder."
            )
            raise SystemExit(1)

        self.graph: Optional[Graph] = None

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
        if not validator(input_data, schema=dataset_description_schema):
            log.error(
                "The dataset description document did not validate. These errors were "
                "reported:"
            )
            log.error(pformat(validator.errors))
            raise SystemExit(1)
        log.debug("Input data validated.")

        file_namespace = input_data["file_namespace"]

        # initialize graph
        graph_uuid = uuid.uuid5(uuid.NAMESPACE_URL, file_namespace)
        graph_iri = f"{OBJECTS_NAMESPACE}{graph_uuid}"
        graph = self.graph = Graph(identifier=graph_iri)

        # describe graph
        s = URIRef(graph_iri)
        for p, o in [
            (RDF.type, m4p0.RDFGraph),
            (RDFS.label, Literal(f"{file_namespace} @ {self.import_time_string}")),
            (edm.dataProvider, URIRef(input_data["data_provider"])),
            (DC.date, Literal(self.import_time)),
        ]:
            graph.add((s, p, o))

        # TODO mind the 'digital_app' at a later stage

    def process_images_data(self):
        if self.source_files.get("images") is None:
            log.debug("No images' metadata found.")
            return
        log.info("# Processing images' metadata.")

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
