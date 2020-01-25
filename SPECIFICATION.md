# Überschrift

Präambel

## Nomenklatur und Konventionen

*Datenset* meint hier alle zu einer Teilmenge der Digitalen Objekte gehörenden
Metadaten, deren Struktur hier dokumentiert ist. Alle Tripel, die diese
Metadaten repräsentieren, werden in Bezug auf diese Teilmenge identifizierbar
in benamten Graphen gespeichert. In Abgrenzung dazu kann von einem *RDF-Dataset*
die Rede sein, wo ein [solches](https://www.w3.org/TR/rdf11-datasets/) gemeint
ist.

In den Turtle/TriG-Beispielen und Ausdrücken zu derivierten Werten sind die in
geschweiften Klammern gefassten Namen als mit den Werten aus den entsprechenden
Tabellenspalten oder anderen zuvor derivierten zu lesen.

Die Ausdrücke zu derivierten Werten können die Funktion `uuid()` zur Bildung
deterministischer UUID aus den in den Klammern angegebenen Eingabewerten
enthalten.

In den Datensets werden im Grundsatz Freitextangaben erwartet.


## Workflow

- Dateien und Metadaten sind von Teilnehmenden geliefert worden
- Publikation der Digitalen Objekte
  - die Dateien werden in den `file_namespace` (s.u.) auf dem Webserver kopiert
- Metadata Import
  - eine *Beschreibung des Datensets* wird erstellt
  - die gelieferten Excel-Tabellen werden als CSV-Dateien und zusammen mit
    vorigem kanonisch benamt in einem *Import-Ordner* gespeichert
  - das Import-Skript wird mit der Angabe von Import-Ordnern aufgerufen


## Anforderungen an das Verhalten der Importroutine

- Fehler bei der Validierung führen zum Abbruch eines Imports
- Fehler beim Einspielen der generierten Tripel lassen den Vorgang abbrechen
- Der gesamte Vorgang wird detailliert geloggt und in einer Log-Datei je
  Import bereit gestellt
- Datensets sind wie im Weiteren definiert eindeutig identifizierbar, ein
  erneuter Import eines identischen Datensets ersetzt bei einem vorigen
  angelegte Daten


## Datensets

Ein vollständiges Datenset besteht aus mehreren Tabellen, die in einem Ordner
gruppiert sind und jeweils:

- das Datenset beschreiben
- Metadaten zu den Digitalen Objekten (DO) enthalten
  - differenziert nach Medientypen (Image, Audio/Video, 3D) in jeweils einer
    Tabelle
- Metadaten zu den Bezugsentitäten der vorigen enthalten

Jedes Datenset bezieht sich auf genau einen Ordner auf dem Webserver. Ob alle
dort vorliegenden Dateien mit Metadaten bedacht wurden, kann nur durch einen
Vergleich der jeweiligen Anzahl verifiziert werden. Demzufolge *muss* der
später genannte `file_namespace` immer genau die in einem Datenset
beschriebenen Digitalen Objekte enthalten.


### Beschreibung des Datensets

Dieses Dokument mit dem Namen `dataset.yml` ist ein einfaches Mapping mit diesen
Feldern:

- `file_namespace` (obligatorisch, global einmalig)
  - Beispielsweise:
    - `https://objects.museum4punkt0.de/narrenschopf/`
    - `https://objects.museum4punkt0.de/deutsches_museum/`
  - wird auch für die Definition eines Erstellungsevents (`E65_Creation`), wobei
    jedoch nach Media Types differenziert wird, gebraucht
- `data_provider` (obligatorisch)
  - IRI der liefernden Institution

Diese Tabelle wird nicht von den liefernden Institutionen erstellt.

Derivierte Werte:

- `graph_uuid` <- `uuid({file_namespace})`
- `graph_iri` <- `https://enter.museum4punkt0.de/resource/{graph_uuid}`
- `import_time` <- aktuelle Zeit als `xsd:dateTime`

Je Beschreibung eines Datensets werden folgende Tripel erzeugt, sofern sie noch
nicht existieren, bzw. ergänzt:

```turtle
{graph_iri}
    a m4p0:RDFGraph ;
    rdf:label "{file_namespace} @ {import_time}" ;
    edm:dataProvider <{data_provider}> ;
    dc:date "{import_time}"^^xsd:dateTime .
```

### Tabelle für Dateimetadaten

Die Tabelle, die *jede* gelieferte Datei beschreibt, wird zur Bildung der
Aussagen über DO gebraucht und enthält folgende Spalten:
Das *_Kernset_* besteht aus:
- `Dateiname` (obligatorisch, lokal einmalig)
- `Rechtehinweis` (schließt `Lizenz` aus)
- `Lizenz` (schließt `Rechtehinweis` aus)
  - muss das Muster einer URL zu einer CC-Lizenz matchen
  - erfordert einen Wert für `licensor` in der Datensetbeschreibung
- `Lizenzgeber` (obligatorisch bei `Lizenz`-Angabe)
- `Bezugsentität` (optional)
  - stellt den Bezug zu einem Museumsobjekt dar, die in einer weiteren Tabelle
    erfasst werden
- `URL` (optional)
  - muss den regulären Ausdruck `https?://.*` matchen

Set für Medientyp *_image_* entspricht dem Kernset.

Set für Medientyp *_video/audio_* enthält über das Kernset hinaus:

- `Dauer` (optional)
  - muss dem Muster `hh:mm:ss` entsprechen

Das Set für Medientyp *_3D_* enthält über das Kernset hinaus:

- `Vorschaubild` (obligatorisch)
- `Geometrieart` (optional)
  - Auswahl aus einer vordefinierten Liste
- `3D-Dateityp` (optional)
- `Geometrieauflösung` (obligatorisch)
  - Auswahl aus einer vordefinierten Liste (`low`, `mid`, `high`)
- `Vertexfarben` (optional)
  - Auswahl aus: (*leer*, `true`, `false`)
- `Texturen` (optional)

Derivierte Werte:

- `Bezugsentität_uuid` <- `uuid({graph_uuid} + {Bezugsentität})`
- `Bezugsentität_iri` <- `https://enter.museum4punkt0.de/resource/{Bezugsentität_uuid}`
- `data_object_iri` <- `"{file_namespace}/{Dateiname}"`
  - beim Import wird per `HEAD`-Request geprüft, ob unter der IRI eine
    Resource verfügbar ist
- `media_type` <- wird aus der Fileextension abgeleitet
  - das Mapping dafür ist in der Konfigurationsdatei definiert und kann
    erweitert werden, z.B.:
    ```yaml
    tif: https://www.iana.org/assignments/media-types/image/tiff
    tiff: https://www.iana.org/assignments/media-types/image/tiff
    zip: https://www.iana.org/assignments/media-types/application/zip
    ```
- `creation_uuid` <- `uuid({file_namespace} + {media_type})`
- `creation_iri` <- `https://enter.museum4punkt0.de/resource/{creation_uuid}`


Je distinkter `creation_iri` werden folgende Tripel erzeugt:

```turtle
GRAPH {graph_iri} {
  <{creation_iri}>
    a crm:E65_Creation ;
    m4p0:hasCreationPhase <https://www.museum4punkt0.de/catalogue/ontology/MaterialProduction> ;
    m4p0:hasCreationMethod <https://www.museum4punkt0.de/catalogue/ontology/Digitisation> .
}
```

Je Zeile/DO werden für das Kernset folgende Tripel erzeugt:

```turtle
GRAPH {graph_iri} {
  <{data_object_iri}>
    a crmdig:D1.Digital_Object ;
    m4p0:fileName "{Dateiname}";
    edm:dataProvider <{data_provider}> ;
    m4p0:hasMediaType <{media_type}> ;
    crm:P94i_was_created_by <{creation_iri}> ;

    dc:rights "{Rechtehinweis}" ;
    # ODER
    dcterms:license "{Lizenz}" ;
    m4p0:licensor "{Lizenzgeber}" ;

    # jeweils optional:
    m4p0:refersToMuseumObject <{Bezugsentität_iri}> ;
    edm:shownAt "{URL}"^^xsd:AnyURI .
}
```

Für die Medientypen "Audio/Video" zusätzlich:

```turtle
GRAPH {graph_iri} {
  <{data_object_iri}> m4p0:length "{Dauer}" .
}
```

Für den Medientypen "3D" zudem:

```turtle
GRAPH {graph_iri} {
  <{data_object_iri}>
    m4p0:fileNameOfThumbnail "{Vorschaubild}" ;
    m4p0:geometryType "{Geometrieart}" ;
    m4p0:fileType "{3D-Dateityp}" ;
    m4p0:qualityOfGeometryRes <m4p0:{Geometrieauflösung}>;
    m4p0:vertexColour "{Vertexfarben}" ;
    m4p0:textureType "{Texturen}" .    
}
```

### Tabelle für Objektmetadaten

Diese Tabelle dient zur Erstellung von `m4p0:MuseumObject`-Instanzen und
beihaltet mindestens folgende Spalten:

- `Identifier` (obligatorisch)
  - hier werden Werte entsprechend `Bezugsentität` der Dateimetadaten-Tabelle
    erwartet
- `Bezeichnung` (obligatorisch)
- `URL` (optional)
  - muss den regülären Ausdruck `https?://.+` matchen

Alle weiteren Spalten sind fakultativ und werden als serialisiertes JSON in
einem noch zu definierenden Property hinterlegt. Diese Spalten werden als
Strings interpretiert, es sei denn sie enthalten Zeilenumbrüche, dann als Array
von Strings.

Derivierte Werte:

- `Bezugsentität_iri` <- wie zuvor, dabei entspricht `identifier` der
  `Bezugsentität`

Je Zeile werden folgende Tripel erzeugt:

```turtle
GRAPH {graph_iri} {
  <{Bezugsentität_iri}>
    a m4p0:MuseumObject ;
    m4p0:museumObjectTitle "{Bezeichnung}";
    rdfs:label "{Bezeichnung}".

    # jeweils optional:
    edm:isShownAt "{URL}";
    m4p0:isDescribedBy _:json .

  # nur wenn voriges Tripel existiert
  _:json  
    a m4p0:JSONObject;
    m4p0:jsonData "{json_string}" .
}
```
