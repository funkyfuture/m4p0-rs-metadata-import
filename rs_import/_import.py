import csv
import json
import uuid
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from pprint import pformat
from pydoc import pager
from types import SimpleNamespace
from typing import Dict, Optional, Set
from urllib.parse import quote as url_quote

import httpx
import yaml
from cerberus import Validator  # type: ignore
from rdflib import BNode, Graph, Literal, Namespace, URIRef  # type: ignore
from rdflib.namespace import RDF, RDFS, XSD  # type: ignore

from rs_import.logging import log, set_file_log_handler
from rs_import.constants import WEB_URL_PATTERN


# URI namespaces

ENTITIES_NAMESPACE = "https://enter.museum4punkt0.de/resource/"

crm = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
crmdig = Namespace("http://www.ics.forth.gr/isl/CRMdig/")
dc = Namespace("http://purl.org/dc/elements/1.1/")
dcterms = Namespace("http://purl.org/dc/terms/")
edm = Namespace("http://www.europeana.eu/schemas/edm/")
m4p0 = Namespace("https://www.museum4punkt0.de/catalogue/ontology/")


# validation schemas

dataset_description_schema = {
    "file_namespace": {
        "type": "string",
        "required": True,
        "regex": WEB_URL_PATTERN + "/$",
    },
    "data_provider": {"type": "string", "required": True, "regex": WEB_URL_PATTERN},
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
    "Bezugsentität": {"type": "string", "empty": False},
    "URL": {"type": "string", "regex": WEB_URL_PATTERN},
}

video_audio_description_schema = {
    **coreset_description_schema,  # type: ignore
    "Dauer": {"type": "string", "regex": r"^\d\d:\d\d:\d\d$"},
}

_3d_description_schema = {
    **coreset_description_schema,
    "3D-Dateityp": {"type": "string"},
    "Geometrieart": {
        "type": "string",
        "allowed": {
            "Punktewolke",
            "Polygonmesh",
            "Flächenmodell (NURBS, CAD)",
            "CT-Daten",
        },
    },
    "Geometrieauflösung": {
        "type": "string",
        "required": True,
        "allowed": ("low", "mid", "high"),
    },
    "Texturen": {"type": "string"},
    "Vertexfarben": {"type": "string", "allowed": ("ja", "nein")},
    "Vorschaubild": {"type": "string", "required": True, "empty": False},
}

entity_description_schema = {
    "Identifier": {"type": "string", "required": True, "empty": False},
    "Bezeichnung": {"type": "string", "required": True, "empty": False},
    "URL": {"type": "string", "regex": WEB_URL_PATTERN},
}

dataset_description_validator = Validator(dataset_description_schema)
coreset_validator = Validator(coreset_description_schema)
audio_video_validator = Validator(video_audio_description_schema)
_3d_validator = Validator(_3d_description_schema)
entity_validator = Validator(
    entity_description_schema, allow_unknown={"type": "string"}
)


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
        self.creation_iris: Set[URIRef] = set()
        self.creation_uuid_ns: Optional[uuid.UUID] = None
        self.encountered_filenames: Set[str] = set()

    def run(self):
        # generate triples from the various sources
        self.process_dataset_description()

        self.process_images_data()
        self.process_audio_video_data()
        self.process_3d_data()

        graph = self.graph
        for creation_iri in self.creation_iris:
            graph.add((creation_iri, RDF.type, crm.E65_Creation))
            graph.add((creation_iri, m4p0.hasCreationPhase, m4p0.MaterialProduction))
            graph.add((creation_iri, m4p0.hasCreationMethod, m4p0.Digitisation))

        self.process_entities_data()

        self.submit()

    def submit(self):
        # submit the triples to the SPARQL-endpoint

        log.info("# Submitting graph data via SPARQL.")

        graph_iri = self.graph.identifier

        turtle_representation: str = self.graph.serialize(
            format="turtle"
        ).decode().splitlines()

        deletion_query = f"""\
        DELETE {{?s ?p ?o}}
        WHERE {{ GRAPH <{graph_iri}> {{?s ?p ?o}} }}
        """

        prefixes = []
        for i, line in enumerate(turtle_representation):
            if line.startswith("@prefix "):
                prefixes.append("PREFIX " + line[8:-2])
            else:
                break

        prefixes_header = "\n".join(prefixes) + "\n"
        statements = "\n".join(turtle_representation[i + 1 :])  # noqa: E203

        insert_query = f"""\
        {prefixes_header}

        INSERT {{
          GRAPH <{graph_iri}> {{
            {statements}
          }}
        }} WHERE {{}}
        """

        if self.config.review:
            pager(insert_query)
            review_passed = input("Proceed? [yN]: ").lower()
            if not review_passed or review_passed[0] != "y":
                log.critical("User aborted after reviewing the SPARQL query.")
                raise SystemExit(1)

        log.debug("Generated SPARQL Query:")
        log.debug(insert_query)

        log.info(f"Deleting all existing triples from the graph <{graph_iri}>.")
        self.post_query(deletion_query)

        log.info(
            f"Posting generated triples to {self.config.sparql_endpoint} as "
            f"{self.config.sparql_user}."
        )
        self.post_query(insert_query)

    def post_query(self, query: str):
        response = httpx.post(
            self.config.sparql_endpoint,
            auth=(self.config.sparql_user, self.config.sparql_pass),
            data=query.encode(),
            headers={
                "Content-Type": "application/sparql-update; charset=UTF-8",
                "Accept": "text/boolean",
            },
        )
        try:
            response.raise_for_status()
        except Exception:
            log.exception("Something went wrong")
            raise SystemExit(1)
        else:
            log.info(f"Received response: {response.content.decode()}")

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
        self.creation_uuid_ns = uuid.uuid5(uuid.NAMESPACE_URL, self.file_namespace)

        # initialize graph
        self.graph_uuid = uuid.uuid5(uuid.NAMESPACE_URL, file_namespace)
        graph_iri = f"{ENTITIES_NAMESPACE}{self.graph_uuid}"
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

    def process_images_data(self):
        source_file = self.source_files.get("images")
        if source_file is None:
            log.debug("No images' metadata found.")
            return

        log.info("# Processing images' metadata.")
        self.process_metadata_file(source_file, self.add_core_fields, coreset_validator)
        log.info("Done.")

    def process_audio_video_data(self):
        source_file = self.source_files.get("audio_video")
        if source_file is None:
            log.debug("No audios' or videos' metadata found.")
            return

        log.info("# Processing audios' and videos' metadata")
        self.process_metadata_file(
            source_file, self.add_audio_video_fields, audio_video_validator
        )
        log.info("Done.")

    def process_3d_data(self):
        source_file = self.source_files.get("3d")
        if source_file is None:
            log.debug("No 3D objects' metadata found.")
            return

        log.info("# Processing 3D objects' metadata.")
        self.process_metadata_file(source_file, self.add_3d_fields, _3d_validator)
        log.info("Done.")

    def process_metadata_file(self, source_file, add_method, validator):
        with source_file.open("rt", newline="") as f:
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

                object_data = validator.validated(normalized_row)
                filename = object_data.get("Dateiname", "<missing>")
                if coreset_validator.errors:
                    log.error(
                        "A digital object metadata set did not validate. These errors "
                        f"were reported for the file {filename}:"
                    )
                    log.error(pformat(coreset_validator.errors))

                if filename in self.encountered_filenames:
                    log.error(f"Encountered redundant filename: {filename}")
                    log.critical("Aborting.")
                    raise SystemExit(1)
                self.encountered_filenames.add(filename)

                add_method(
                    URIRef(self.file_namespace + url_quote(filename)),
                    filename,
                    object_data,
                )

    def add_core_fields(self, s, filename, object_data):
        graph = self.graph
        if not httpx.head(s).status_code == 200:
            log.error(f"The resource at {s} is not available.")
            raise SystemExit(1)
        media_type = self.config.media_types[Path(filename).suffix[1:]]
        creation_uuid = uuid.uuid5(self.creation_uuid_ns, media_type)
        creation_iri = URIRef(f"{ENTITIES_NAMESPACE}{creation_uuid}")
        self.creation_iris.add(creation_iri)

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
            graph.add(
                (
                    s,
                    m4p0.refersToMuseumObject,
                    self.create_related_entity_iri(object_data["Bezugsentität"]),
                )
            )
        if "URL" in object_data:
            graph.add(
                (s, edm.shownAt, Literal(object_data["url"], datatype=XSD.anyURI),)
            )

    def add_audio_video_fields(self, s, filename, object_data):
        self.add_core_fields(s, filename, object_data)
        self.graph.add((s, m4p0.length, Literal(object_data["Dauer"])))

    def add_3d_fields(self, s, filename, object_data):
        self.add_core_fields(s, filename, object_data)

        graph = self.graph

        graph.add((s, m4p0.fileNameOfThumbnail, Literal(object_data["Vorschaubild"])))

        geometrieart = object_data.get("Geometrieart")
        if geometrieart:
            graph.add((s, m4p0.geometryType, Literal(geometrieart)))

        dateityp = object_data.get("3D-Dateityp")
        if dateityp:
            graph.add((s, m4p0.fileType, Literal(dateityp)))

        graph.add(
            (s, m4p0.qualityOfGeometryRes, m4p0[object_data["Geometrieauflösung"]])
        )

        vertexfarben = object_data.get("Vertexfarben")
        if vertexfarben:
            graph.add((s, m4p0.vertexColour, Literal(vertexfarben)))

        texturen = object_data.get("Texturen")
        if texturen:
            graph.add((s, m4p0.textureType, Literal(texturen)))

    def process_entities_data(self):
        if self.source_files.get("entities") is None:
            log.debug("No entities' metadata found.")
            return
        log.info("# Processing entities' metadata.")

        graph = self.graph

        with self.source_files["entities"].open("rt", newline="") as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:

                identifier = row.get("Identifier")

                if not entity_validator(row):
                    log.error(
                        "An entity description did not validate. These errors "
                        f"were reported for the identifier {identifier}:"
                    )
                    log.error(pformat(entity_validator.errors))
                    raise SystemExit(1)

                s = self.create_related_entity_iri(identifier)

                if len(set(graph.triples((None, m4p0.refersToMuseumObject, s)))) < 1:
                    log.error(
                        "This identifier is not referenced in the metadata of any "
                        f"digital object in the created graph: {identifier}"
                    )
                    raise SystemExit(1)

                label = Literal(row["Bezeichnung"])
                graph.add((s, RDF.type, m4p0.MuseumObject))
                graph.add((s, m4p0.museumObjectTitle, label))
                graph.add((s, RDFS.label, label))

                if "URL" in row:
                    graph.add((s, edm.isShownAt, URIRef(row["URL"])))

                arbritrary_fields = {
                    k: v for k, v in row.items() if k not in entity_description_schema
                }
                if arbritrary_fields:
                    blank_node = BNode()
                    graph.add((blank_node, RDF.type, m4p0.JSONObject))
                    graph.add(
                        (
                            blank_node,
                            m4p0.jsonData,
                            Literal(json.dumps(arbritrary_fields)),
                        )
                    )
                    graph.add((s, m4p0.isDescribedBy, blank_node))

        log.info("Done.")

    def create_related_entity_iri(self, identifier: str) -> URIRef:
        return URIRef(f"{ENTITIES_NAMESPACE}{uuid.uuid5(self.graph_uuid, identifier)}")
