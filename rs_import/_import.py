from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Dict

import yaml
from rdflib import Graph  # type: ignore

from rs_import.logging import log, set_file_log_handler


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
        self.import_time = datetime.now().isoformat(timespec="seconds")

        log_folder = path / "logs"
        try:
            log_folder.mkdir(exist_ok=True)
        except FileNotFoundError:
            log.error(f"The import folder '{path}' doesn't exist. Aborting.")
            raise SystemExit(1)
        set_file_log_handler(log_folder / f"{self.import_time}.log")

        log.info(f"Setting up import from {path}")

        with (path / "dataset.yml").open("rt") as f:
            self.dataset_description = yaml.load(f, Loader=yaml.SafeLoader)

        self.source_files: Dict[str, Path] = {}
        for name in ("images", "audio_video", "3d", "entities"):
            if (path / f"{name}.csv").exists():
                self.source_files[name] = path / f"{name}.csv"
        if tuple(self.source_files) == ("entities",):
            log.error(
                "At least one of 'images.csv', 'audio_video.csv' or '3d.csv' "
                "must be present in an import folder."
            )

        self.graph = Graph()  # TODO add identifier

    def run(self):
        self.process_dataset_description()

        # generate triples from the various sources
        self.process_images_data()
        self.process_audio_video_data()
        self.process_3d_data()
        self.process_entities_data()

        # submit the triples to the SPARQL-endpoint
        self.generate_graph()
        with NamedGraphBackup():
            self.submit_graph()

    # input data processing

    def process_dataset_description(self):
        log.info("# Processing dataset description.")
        raise NotImplementedError

    def process_images_data(self):
        if self.source_files.get("images") is None:
            log.debug("No images' metadata found.")
            return
        log.info("# Processing images' metadata.")
        raise NotImplementedError

    def process_audio_video_data(self):
        if self.source_files.get("audio_video") is None:
            log.debug("No audios' metadata found.")
            return
        log.info("# Processing audios' metadata")
        raise NotImplementedError

    def process_3d_data(self):
        if self.source_files.get("3d") is None:
            log.debug("Not 3D objects' metadata found.")
            return
        log.info("# Processing 3D objects' metadata.")
        raise NotImplementedError

    def process_entities_data(self):
        if self.source_files.get("objects") is None:
            log.debug("No entities' metadata found.")
            return
        log.info("# Processing entities' metadata.")
        raise NotImplementedError

    # data ingestion

    def generate_graph(self):
        log.info("# Generating graph data.")
        raise NotImplementedError

    def submit_graph(self):
        log.info("# Submitting graph data via SPARQL.")
        raise NotImplementedError
