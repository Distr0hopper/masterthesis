# Besonderheiten der Implementierung

Sammlung der Stellen, die sich für die Arbeit eignen: bewusste Design-Entscheidungen mit Trade-off, die man begründen und gegen Alternativen abgrenzen kann. Pro Punkt: **was** umgesetzt ist, **warum**, welche **Alternativen** es gab, und **wo** im Code.

Empfohlene Gewichtung: Die mit ★ markierten Punkte sind die stärksten Kandidaten für eigene Abschnitte. Die übrigen eignen sich als kürzere Erwähnungen, Punkt 13 und 20 gut für ein Kapitel zur Qualitätssicherung.

---

## 1. Persistenz und ORM

### 1.1 ★ Komposition statt Vererbung für das Composite

- **Was:** `components` ist die gemeinsame Basistabelle (Name, Version, CWL, Ports, Domains, Dateien, Status), unterschieden über den Diskriminator `kind`. Was nur eine Art hat, liegt in 1:1-Detailzeilen `tools` und `workflows`. Ein Eintrag in `workflow_steps` ist die Kante vom Workflow zu seinem Kind, das ein Tool oder ein verschachtelter Workflow sein kann.
- **Warum:** Das ist das GoF-Composite-Pattern, übertragen auf CWLs `Process`-Hierarchie (CommandLineTool/ExpressionTool als Blätter, Workflow als Composite). Gemeinsame Operationen (Listen, Lesen, Veröffentlichen, Löschen) laufen polymorph über `/components`, nur Art-spezifisches über `/tools` und `/workflows`.
- **Alternativen:** Single-Table-Inheritance oder Joined-Table-Inheritance über das ORM. SQLModel kann keine Tabellenklasse abbilden, die von einer anderen Tabellenklasse erbt. Deshalb ist die Hierarchie als Komposition plus Diskriminator modelliert und nicht als Python-Vererbung.
- **Code:** `backend-python/app/domain/models/component.py`, `tool.py`, `workflow.py`, `workflow_step.py`

### 1.2 ★ `load_tree` lädt Ebene für Ebene

- **Was:** Der ganze Baum unter einem Workflow wird in einer Abfrage pro Baumtiefe geladen, jeweils mit festen Eager-Loading-Optionen für genau eine Ebene (`_ONE_LEVEL`: Steps, ihr Kind und dessen Detailzeile). Eine Komponente, die mehrfach erreicht wird, wird nur einmal expandiert. `find_ancestors` ist das Gegenstück („wer verwendet mich?“), ebenfalls ebenenweise.
- **Warum:** Eager Loading bricht ab, sobald ein Pfad eine Beziehung erneut besucht (component → steps → component). Das nächste Kind bliebe dann einem Lazy Load überlassen. Eine `AsyncSession` kann aber nicht lazy nachladen: Ein Attributzugriff außerhalb eines awaiteten Kontexts wirft `MissingGreenlet`.
- **Dazu gehört:**
  - `find_by_id_fresh` mit `populate_existing`: Nach einem Schreibvorgang würde ein Treffer in der Identity Map Beziehungen ungeladen lassen, die nur über den Fremdschlüssel gesetzt wurden.
  - `eager_defaults`: Vom Server erzeugte Zeitstempel kommen per `RETURNING` zurück, statt nachgeladen werden zu müssen.
- **Alternativen:** Rekursive CTE (eine Abfrage, aber Abbildung zurück auf ORM-Objekte aufwändig) oder synchrone Session (verschenkt das Async-Modell von FastAPI).
- **Code:** `backend-python/app/domain/repository/components_repository.py` (`load_tree`, `find_ancestors`, `_ONE_LEVEL`, `find_by_id_fresh`)

### 1.3 ★ Der Name als Schlüssel der Lineage, Versionen über die ID gebunden

- **Was:** Alle Versionen einer Komponente teilen ihren Namen. `(name, version)` ist eindeutig, und der Name ist über beide Arten hinweg eindeutig. Ein Workflow-Schritt zeigt immer auf eine konkrete Versionszeile (ID), nie auf „die neueste Version“. Favoriten hängen am Namen, gelten also für die ganze Lineage.
- **Warum:** Reproduzierbarkeit, denn ein Workflow läuft immer mit genau den Versionen, mit denen er gebaut wurde. Listen zeigen trotzdem pro Lineage nur die neueste passende Version, ermittelt in einer Abfrage per `DISTINCT ON (name)`.
- **Konsequenz:** Weil der Name der Schlüssel ist, wäre Umbenennen eine Änderung an allen Versionen. Deshalb ist der Name fest, sobald eine Version öffentlich ist (siehe 3.5).
- **Alternative / Ausblick:** Eine eigene `lineages`-Tabelle mit stabiler ID, der Name wäre dann ein frei änderbarer Anzeigename (wie Repos auf GitHub). Fachlich sauberer, aber ein großer Schema-Umbau.
- **Code:** `component.py` (`uq_components_name_version`), `components_repository.py` (`find_paginated`, `find_all`), `favorites_repository.py`

### 1.4 Abgeleiteter Zustand in der Datenbank

- **Was:** `Component.superseded_by` ist eine `column_property` mit einer korrelierten Unterabfrage: Gibt es eine neuere veröffentlichte Version derselben Lineage? Sie wird mit jeder Zeile geladen.
- **Warum:** Jede Liste und jede Detailseite braucht diese Information, etwa um „Publish“ oder „Undeprecate“ auszublenden. Ohne die Unterabfrage bräuchte man N+1 Abfragen. Sie dient nur der Anzeige, die fachliche Regel prüft der Service separat gegen die Versionen selbst.
- **Code:** `component.py` (Ende der Datei, `_newest_newer_published`)

### 1.5 Enums als Strings, keine nativen Postgres-Enums

- **Was:** `kind`, `status`, `source` und `match_status` sind `String`-Spalten.
- **Warum:** Neue Werte erfordern keine `ALTER TYPE`-Migration. Die Kehrseite: Geladene Werte sind einfache `str`, deshalb werden sie als `ComponentKind(...)` gewrappt.

---

## 2. Transaktionen

### 2.1 ★ Strikte Unit of Work

- **Was:** Repositories fügen hinzu, löschen und flushen, committen aber nie. Nur die vom Router aufgerufenen Use Cases öffnen `async with self.uow:` und committen einmal. Über Flags in `session.info` wird durchgesetzt:
  - Eine verschachtelte Unit wirft einen Fehler („ein Use Case ruft keinen anderen auf“).
  - Ein Repository-Schreibzugriff außerhalb einer Unit wirft einen Fehler, statt still verloren zu gehen.
  - Eine Unit, die mit ungespeicherten Änderungen endet, wirft einen Fehler und rollt zurück.
- **Warum:** Ein Use Case wird ganz oder gar nicht angewendet. Die Transaktionsgrenzen sind explizit und überprüfbar.
- **Alternativen:** `@Transactional`-artige Dekoratoren (implizit, Propagation schwer nachvollziehbar) oder Commit in jedem Repository (keine Atomarität über mehrere Repositories).
- **Code:** `backend-python/app/application/unit_of_work.py`, `app/infrastructure/db/unit_of_work.py`, `app/infrastructure/db/session.py` (`require_unit_of_work`)

### 2.2 Kein HTTP innerhalb einer Transaktion

- **Was:** Alles, was den Format-Service fragt, passiert vor dem Öffnen der Unit: Tools werden mit `ToolsService.prepare` gelesen, Workflow-Dokumente mit `ComponentsService.read_ports`. In der Unit bleibt nur die Datenbankarbeit. Beim Upload verschachtelter Workflows werden dafür alle neuen Tools und alle zu speichernden Workflow-Dokumente vorab vorbereitet.
- **Warum:** Eine Transaktion, die auf HTTP wartet, hält ihre Locks (neue Zeilen, beim Builder-Sync sogar die umbenannte Lineage) so lange, wie der Service braucht, im schlimmsten Fall bis zum Timeout.
- **Code:** `tools_service.py` (`prepare`), `components_service.py` (`read_ports`, `assign_ports`), `workflows_service.py` (`_persist_upload`), Test `tests/api/test_format_service_outside_transactions.py`

### 2.3 Handgeschriebene Migrationen

- **Was:** Migrationen werden nie per `--autogenerate` erzeugt. Tabellen werden nie gelöscht, sondern umgebaut, weil die Dev-Datenbank echte Daten enthält.
- **Code:** `backend-python/alembic/versions/`, z. B. `…composite_components.py` (Umbau auf das Composite)

---

## 3. Fachliche Regeln: Lifecycle

### 3.1 ★ Lifecycle als Übergangstabellen in reinen Funktionen

- **Was:** Die erlaubten Statuswechsel (DRAFT, PUBLISHED, DEPRECATED) und Step-Zustände (UNMATCHED, SUGGESTED, CONFIRMED, INLINE) stehen als Tabellen in einem Modul. Es ist die einzige Stelle, die `status` oder den Zustand eines Schritts schreibt. Alles sind reine Funktionen über bereits geladene Komponenten.
- **Drei Fragen, die man nie miteinander beantworten darf:**
  - **Draft?** Immer `status == DRAFT`, nie „nicht veröffentlicht“. Sonst würde ein deprecatetes Kind für einen Draft gehalten und still mitveröffentlicht.
  - **Für alle sichtbar?** `PUBLIC_STATUSES` = PUBLISHED oder DEPRECATED.
  - **Gelistet und für neue Verwendung angeboten?** `LISTED_STATUSES` = nur PUBLISHED.
- **Code:** `backend-python/app/domain/composite/lifecycle.py`, Doku `backend-python/docs/status-lifecycle.md`

### 3.2 ★ Veröffentlichen über den ganzen Baum

- **Was:** Ein öffentlicher Workflow darf in keiner Tiefe Drafts ausführen, denn Drafts sind nur für ihren Besitzer sichtbar, und der Workflow wäre für alle anderen kaputt.
  - Eigene Drafts im Baum können per Opt-in mitveröffentlicht werden.
  - Drafts anderer Nutzer blockieren.
  - Deprecatete Kinder blockieren nur dort, wo das Veröffentlichen eine **neue** Abhängigkeit schafft (direkt unter der Wurzel oder unter einem mitveröffentlichten Draft). Unter einem bereits öffentlichen verschachtelten Workflow ist die Abhängigkeit alt und nicht Sache des Handelnden.
- **Code:** `lifecycle.py` (`can_publish`, `PublishCheck`), `components_service.py` (`publish`)

### 3.3 ★ Zurückziehen mit Zeitfenster und Prüfung aller Vorfahren

- **Was:** Eine veröffentlichte Version kann nur innerhalb von `UNPUBLISH_WINDOW_SECONDS` (Standard 24 h) nach der ersten Veröffentlichung wieder zum Draft werden, ähnlich wie bei npm. Danach ist nur noch Deprecate möglich, und nur Drafts lassen sich löschen. Vor Unpublish oder Löschen werden **alle** öffentlichen Workflows darüber geprüft, in jeder Tiefe, nicht nur die direkten Eltern. Fremde blockieren, eigene werden per Opt-in mit zurückgezogen.
- **Superseding:** Wird vN veröffentlicht, werden ältere veröffentlichte Versionen automatisch deprecated („Superseded by vN“). So bringt ein späteres Unpublish von vN nicht still eine alte Version zurück.
- **Warum:** Eine veröffentlichte Version ist ein Versprechen an andere, die sie gesehen, ausgeführt, verschachtelt oder zitiert haben. Ihr Inhalt ändert sich nie, Änderungen entstehen als neue Version.
- **Code:** `lifecycle.py` (`retract_impact`, `within_unpublish_window`, `superseded_by`), `components_service.py` (`unpublish`, `_require_retractable`, `get_impact`)

### 3.4 Zykluserkennung über die Lineage statt über die ID

- **Was:** Ein Schritt darf keinen Workflow ausführen, der irgendwann den eigenen Workflow enthält, und das wird über den **Namen** verglichen.
- **Warum:** Wenn v1 eines Workflows seine eigene v2 verschachtelt, ist das ebenso eine Selbstreferenz. Die nächste Version würde die übernächste verschachteln, ohne Ende. Geprüft wird beim Binden eines Schritts, beim Upload (Wiederverwendung) und beim Builder-Sync. Die Builder-Palette blendet solche Workflows schon vorher aus (`nestableIn`).
- **Code:** `domain/composite/tree.py` (`would_create_cycle`, `contains_lineage`), `workflows_service.py` (`_require_acyclic`)

### 3.5 Name fest nach der ersten Veröffentlichung

- **Was:** Ein Builder-Canvas lässt sich umbenennen, solange alle Versionen seiner Lineage Drafts sind. Sobald eine Version öffentlich ist, lehnt der Sync eine Umbenennung mit 409 ab, und der Builder sperrt das Namensfeld (`linkedWorkflow.nameLocked`).
- **Warum:** Sonst würde sich eine öffentliche Version für alle ändern, ohne dass eine neue Version entsteht, und das `label` in ihrem CWL passte nicht mehr zu ihrem Namen. Paket-Registries wie npm und PyPI handhaben Namen genauso.
- **Code:** `lifecycle.py` (`name_locked`), `workflows_service.py` (`upsert_from_draft`)

---

## 4. API-Design

### 4.1 ★ Command-Registry und HATEOAS

- **Was:** Zustandsändernde Aktionen (Publish, Unpublish, Deprecate, Repackage, …) sind einmal in einer Registry deklariert. Dispatch, Berechtigungsprüfung und die `_links` der Antwort laufen alle über diese Registry. Ein neuer Befehl braucht also nur ein Enum-Mitglied und einen Registry-Eintrag.
  - `allowed`: **Wer** darf den Befehl ausführen? Abgelehnt mit 403.
  - `available`: **Passt** der Befehl zum aktuellen Zustand (Status, Unpublish-Fenster, Superseding)? Davon hängt nur ab, ob der Link angeboten wird. Der Service lehnt trotzdem mit einer eigenen 409 ab, die sagt, warum.
  - Das Frontend entscheidet allein anhand der Link-Rels, welche Aktionen es anzeigt. Es gibt dort keine eigene Kopie der Zustandsmaschine.
- **Code:** `app/application/commands/registry.py`, `components_service.py` und `tools_service.py` (`COMPONENT_COMMANDS`, `TOOL_COMMANDS`), `app/api/link/component.py`, Frontend `src/api/permissions.ts`

### 4.2 Autorisierung im Router, Informationsverbergung

- **Was:** Der Router lädt die Entität, prüft den Permission-Validator und übergibt die schon geladene Entität an den Service. Services nehmen keine `user_id` für die Autorisierung.
- **Informationsverbergung:**
  - Fremde Drafts antworten mit **404 statt 403**, damit nicht bestätigt wird, dass es sie gibt.
  - Ein Name, der von einem fremden Draft belegt ist, gilt als belegt, aber ohne den Halter zu nennen.
  - Ein Builder-Canvas ist vom Client geschriebenes JSON. Darin genannte Komponenten-IDs werden serverseitig nur aufgelöst, wenn der Besitzer des Canvas sie lesen darf.
- **Code:** `app/api/permission/`, `app/api/routers/`, `workflow_draft_service.py` (`_resolve_components`)

### 4.3 Exceptions als fachliche Sprache

- **Was:** Fachliche Regeln werfen eigene Domain- oder Application-Exceptions, die zentral auf HTTP-Codes abgebildet werden. Unerwartetes bleibt ungefangen und erscheint als 500.
- **Code:** `app/api/exception/handlers.py`, `app/application/exception/`

---

## 5. CWL-Verarbeitung

### 5.1 ★ Archiv-Layout mit Umschreiben nur in der Kopie

- **Was:** Download und Builder-Export legen den ganzen Baum ab. Jeder verschachtelte Workflow kommt mit seinen Schritten und Imports in einen eigenen Ordner (`inner/inner.cwl`, daneben seine Schritte). Das `run:` im Eltern-Dokument wird nur in der **Kopie im Archiv** auf diesen Ordner umgeschrieben. Das gespeicherte CWL einer öffentlichen Version bleibt byte-identisch.
- **Warum:** CWL löst `run:` relativ zum Dokument auf, das es schreibt. In einem flachen Archiv passen zwei Versionen desselben Tools nicht nebeneinander. Genau das erzeugt aber das Superseding: Der Eltern-Workflow nutzt schon v2, der verschachtelte noch v1.
- **Code:** `domain/composite/tree.py` (`ArchiveLayout`), `components_service.py` (`get_download`, `laid_out_documents`), `infrastructure/cwl/workflow_parser.py` (`retarget_steps`), `infrastructure/cwl/workflow_generator.py` (`assemble_cwl_zip`)

### 5.2 Normalisierung beim Upload

- **Was:**
  - Inline-CommandLineTools werden zu eigenständigen Komponenten extrahiert. Ihr `run:` im gespeicherten Pipeline-Dokument wird auf einen Dateinamen umgestellt, damit `run_reference` immer stimmt.
  - Inline-ExpressionTools und inline-Workflows bleiben eingebettet (`run_reference` = „(inline …)“, Zustand INLINE).
  - Archive dürfen verschachtelte Workflow-Dateien enthalten. Die Wurzel ist das Dokument, das kein anderes ausführt.
  - `$import`/`$include`-Ziele werden transitiv aufgelöst und mit jeder Komponente gespeichert, damit sie im Katalog eigenständig ist.
  - Ein einzelner Wrapper-Ordner (macOS Finder) wird entfernt, ebenso `__MACOSX/` und `._*`-Sidecar-Dateien.
  - Jeder Schritt braucht eine explizite Entscheidung (wiederverwenden, neue Version, neu anlegen). Nichts wird automatisch angelegt.
  - Sicherheit: Für entpackte Archive gilt ein Größenlimit (Schutz vor Zip-Bombs).
- **Code:** `workflows_service.py` (`parse_workflow_upload`, `_persist_upload`), `infrastructure/cwl/workflow_parser.py`

### 5.3 Generierung aus dem Workflow-Builder

- **Was:** Ein Canvas (React-Flow-Knoten und -Kanten) wird zu einem CWL-v1.2-Workflow.
  - Die Reihenfolge der Schritte entsteht per topologischer Sortierung (Kahn). Die Knotenposition auf dem Canvas sagt nichts über die Ausführungsreihenfolge aus, und sortierte Warteschlangen machen das Ergebnis deterministisch, damit die CWL nicht zwischen Exporten springt.
  - Die Verdrahtung kommt aus den Handles der Kanten, die die echten Parameternamen tragen.
  - Workflow-Inputs werden pro Schritt mit einem Namensraum versehen (`step__port`), damit gleichnamige Ports nicht kollidieren.
  - `SubworkflowFeatureRequirement` wird nur gesetzt, wenn ein Schritt einen Workflow ausführt.
  - Jedes Speichern synchronisiert den Canvas als Draft-Workflow in „My Components“: In-place, solange die neueste Version ein Draft ist, sonst als nächste Version.
- **Code:** `infrastructure/cwl/canvas_graph.py`, `infrastructure/cwl/workflow_generator.py`, `workflow_draft_service.py`, `workflows_service.py` (`upsert_from_draft`)

### 5.4 ★ Portkompatibilität über eine Ontologie

- **Was:** Ob ein Output zu einem Input passt, beantwortet der SOS File Format Service anhand der EO-Formats-Ontologie (gleiche Klasse, Unterklasse oder äquivalent).
  - Das Ergebnis ist dreiwertig: compatible, unverified (kein Format, keine gemeinsame Ontologie, Service nicht erreichbar) und incompatible. Nur incompatible blockiert eine Verbindung.
  - Ein prozessweiter Cache speichert nur **eindeutige** Antworten. Antwortet der Service nicht, wird beim nächsten Mal neu gefragt.
  - Handgeschriebene Format-Labels (z. B. „RDS“) dienen nur der Anzeige und machen eine Verbindung nie „verifiziert“.
  - Die Palette im Builder wird nach Kompatibilität mit den Knoten auf dem Canvas sortiert, über die **ganze** gefilterte Menge vor dem Paging. Sonst könnte ein guter Treffer auf einer späteren Seite nie auftauchen. Favoriten entscheiden nur Gleichstände innerhalb einer Bewertungsstufe.
- **Code:** `app/domain/compatibility/` (`port_check.py`, `ranking.py`), `compatibility_service.py`, Doku `backend-python/docs/port-compatibility.md`

### 5.5 Vertrauen beim automatischen Packaging

- **Was:**
  - Die Raw-URLs im generierten Dockerfile/CWL werden auf einen Commit fixiert, nicht auf einen Branch. Eine veröffentlichte Version übernimmt keine späteren Pushes.
  - `expected_commit_sha`: Hat sich das Repo zwischen Vorschau und Speichern bewegt, wird abgelehnt, statt eine nie geprüfte CWL zu speichern.
  - Formate, die der Packager erzeugt, werden verworfen. Er kann sie nicht verbürgen, nur von Menschen geschriebene Formate gelten als vertrauenswürdig.
  - Handgeschriebene Labels werden beim Repackaging auf die neue Version übertragen.
- **Code:** `automated-packaging/moveapps_cwl_packager/`, `tools_service.py` (`preview_package`, `package_next_version`, `_check_expected_commit`), `components_service.py` (`parse_ports`)

### 5.6 R-Pakete aus dem datierten Snapshot, Build scheitert laut

- **Was:** Die Pakete aus `appspec.json` kommen aus dem Repository, das das Wrapper-Image (rocker) festlegt: ein datierter P3M-Snapshot mit Linux-Binärpaketen. Nach der Installation prüft der Build, ob alle Pakete ladbar sind, und bricht sonst mit ihren Namen ab.
- **Warum:** Reproduzierbar wie der gepinnte Commit, etwa 5-mal schnellere Builds, und Fehler landen dort, wo sie entstehen. `install.packages()` meldet einen Fehlschlag nur als Warnung, vorher fiel ein fehlendes Paket deshalb erst zur Laufzeit auf. Gefunden wurde das bei der Evaluation gegen alle movestore-Apps.
- **Trade-off:** Binärpakete setzen die Systembibliotheken voraus, gegen die sie gebaut wurden (`keyring` braucht `libsecret`). Aus dem Quellcode kompiliert käme `keyring` ohne aus.
- **Alternativen:** aktuelles CRAN als Quellcode (vorher: langsam, nicht reproduzierbar, scheitert an fehlenden Headern), die `renv.lock` des Repos (nur 62 von 88 Apps haben eine), Systembibliotheken einzeln nachrüsten (Sonderfälle).
- **Code:** `generators.py` (`generate_dockerfile_content`), Details in `evaluation-movestore.md`

---

## 6. Querschnittsthemen

### 6.1 Passwortlose Anmeldung mit Sliding Session

- **Was:** Ein Einmalcode per E-Mail wird gegen ein JWT getauscht, neue Adressen werden automatisch angelegt. Das Token wird bei **Aktivität** erneuert (API-Request oder Rückkehr in den Tab), nie per Timer. Sonst würde ein offener Tab die Session ewig am Leben halten. Fehlversuche werden committet, bevor der Fehler geworfen wird, damit das Versuchslimit nicht durch einen Rollback ausgehebelt wird.
- **Code:** `otp_service.py`, `auth_service.py`, Frontend `src/api/auth/session.ts`

### 6.2 ★ Verträge als Tests

- **Was:**
  - Die eingecheckte `openapi.json` wird gegen die laufende API getestet (`make openapi` erzeugt sie neu).
  - Ein Frontend-Test vergleicht die Enums und Eingabelimits des Frontends mit der Spec.
  - Ein Test stellt sicher, dass **jede** fachliche Exception einen HTTP-Handler hat. Eine vergessene käme sonst als 500 beim Client an.
- **Code:** `backend-python/tests/infrastructure/test_schema.py`, `frontend/src/api/contract.test.ts`, `backend-python/tests/api/test_exception_handlers.py`

### 6.3 Teststrategie mit echtem Postgres

- **Was:** Die Datenbanktests laufen gegen ein echtes Postgres. Pro Lauf wird die Testdatenbank neu angelegt und alle Migrationen laufen von Null, was nebenbei die Migrationen selbst testet. Jeder Test läuft in einer äußeren Transaktion. Die Units of Work darin committen in Savepoints, und am Ende wird alles zurückgerollt. Ohne Postgres werden diese Tests übersprungen. Dazu kommen Playwright-E2E-Tests gegen ein eigenes Backend mit eigener Datenbank.
- **Code:** `backend-python/tests/conftest.py`, `frontend/e2e/`
