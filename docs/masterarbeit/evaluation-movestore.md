# Evaluation: Automatisches Packaging der MoveApps aus github.com/movestore

Wie viele MoveApps lassen sich mit dem Packager automatisch als CWL-Tool verpacken, und wie viele laufen danach tatsächlich? Gemessen über **alle** Repositories der Organisation `movestore`, Stand 27./28.10.2026.

- **Skript:** `automated-packaging/evaluation/evaluate_movestore.py` (für den Anhang)
- **Ergebnisse:** `automated-packaging/evaluation/output/` – `summary.md` und `results.csv` pro Stand, Logs pro App unter `apps/<repo>/`
- **Stände:** `baseline/` (vor den Korrekturen), `after-ac/` (nach A und C), Wurzelverzeichnis (nach A, B und C)

---

## 1. Methode

Jedes Repository durchläuft dieselbe Kette. Jede App endet in genau einem Status, die Zahlen bilden also einen Trichter.

1. **Erfassen:** Alle Repositories der Organisation über die GitHub-REST-API.
2. **Einordnen:** Anhand der Dateien im Repository:
   - Template (`is_template`),
   - R-Function-App (`RFunction.R`),
   - Shiny-App (`ShinyModule.R`),
   - Python-App (`app/app.py`),
   - keine App (z. B. die Website `movestore.github.io`, Newsletter, Datensätze).

   Nur R-Function-Apps liegen im Scope des Packagers. Archivierte Repositories und Forks werden **nicht** ausgeschlossen, sondern markiert.
3. **Paketieren:** `package_repo()` des Packagers erzeugt die CWL-Beschreibung.
4. **Image bauen:** `docker build` aus dem `dockerFile`, das in der CWL eingebettet ist. Der Schritt ist vom Lauf getrennt, damit Abhängigkeitsfehler von Fehlern der App unterscheidbar sind.
5. **Ausführen:** `cwltool` mit einem festen Testdatensatz (`input-files/input1.rds`, ein `move2`-Objekt mit 28 Tracks und 99 668 Ortungen). Alle Settings stehen auf ihrem Default aus `appspec.json`, Settings ohne Default bleiben `null`.

**Erfolgskriterium:** `cwltool` endet mit Exit-Code 0, und die App hat `output.rds` geschrieben. „Läuft“ heißt also: läuft mit den Defaults auf einem Standarddatensatz. Ob das Ergebnis fachlich richtig ist, wird nicht geprüft.

Netzwerkfehler gegenüber GitHub werden wiederholt und nie als Ergebnis einer App gezählt.

---

## 2. Grundgesamtheit

| Kategorie | Repositories | davon archiviert | davon Forks |
| --- | ---: | ---: | ---: |
| R-Function-App (im Scope) | 88 | 7 | 4 |
| Shiny-App | 27 | 4 | 5 |
| Python-App | 6 | 0 | 1 |
| Template | 4 | 0 | 0 |
| keine App | 10 | 1 | 0 |
| **gesamt** | **135** | | |

---

## 3. Ergebnis

Die erste Messung hat drei Schwächen des Packagers aufgedeckt (A–C, Abschnitt 4). Nach deren Behebung wurde neu gemessen.

| Stufe (88 R-Function-Apps) | vorher | nach A+C | nach A+B+C |
| --- | ---: | ---: | ---: |
| paketiert (CWL erzeugt) | 74 (84,1 %) | 78 (88,6 %) | **78 (88,6 %)** |
| Image gebaut | 74 (84,1 %) | 78 (88,6 %) | **71 (80,7 %)** |
| erfolgreich gelaufen | 27 (30,7 %) | 28 (31,8 %) | **28 (31,8 %)** |
| Build-Zeit aller Images | 47 min | – | 9 min |

Dass im Stand „vorher“ jedes paketierte Image gebaut wurde, war ein Messfehler des Packagers und kein gutes Zeichen. Fehlgeschlagene Paketinstallationen fielen erst zur Laufzeit auf (siehe B). Der Rückgang bei „Image gebaut“ nach B ist deshalb gewollt: Die Fehler landen jetzt dort, wo sie entstehen.

---

## 4. Korrekturen am Packager

Bedingung für jede Korrektur: Sie muss allgemein sein, also jede App betreffen können. Sonderfälle für einzelne Apps oder Pakete wurden bewusst nicht eingebaut.

### A. Setting-IDs, die keine JavaScript-Bezeichner sind

- **Problem:** Die CWL schreibt `app-configuration.json` über eine JavaScript-Expression. Aus der Setting-ID `loc.err` wurde `loc.err: inputs.loc.err`, ein `SyntaxError`. Dasselbe passiert bei Bindestrichen (`auxiliary-file-a`). Betroffen waren 5 Apps.
- **Lösung:** Schlüssel in Anführungszeichen, Zugriff über eckige Klammern: `"loc.err": inputs["loc.err"]`.
- **Ergebnis:** Alle 5 Apps kommen über die Expression hinaus. Keine davon läuft danach erfolgreich, die Gründe liegen in den Apps selbst bzw. bei fehlenden Paketen.
- **Code:** `generators.py` (`_build_js_entry`)

### B. Installation der R-Pakete

- **Problem:**
  - Das generierte Dockerfile installierte die Pakete aus `appspec.json` mit `repos="https://cloud.r-project.org"`, also aus dem jeweils aktuellen CRAN, als Quellcode. Der Override stammt aus dem ersten Prototyp und hatte keinen fachlichen Grund. Er ist ein verbreitetes Muster für schlichte R-Images, in denen kein Repository eingestellt ist.
  - Das Wrapper-Image (rocker) stellt aber bereits einen **datierten Snapshot** von Posits Paket-Repository mit Linux-Binärpaketen ein (`p3m.dev/cran/__linux__/noble/2025-10-30`). Der Override hob diese Festlegung wieder auf.
  - Folgen:
    - Pakete wurden unter amd64-Emulation kompiliert. Das ist langsam und scheiterte an fehlenden System-Headern (`ctmm` → `Rmpfr` → `mpfr.h`).
    - Downloads liefen in Rs Standard-Timeout von 60 s (`move`).
    - Die Builds waren nicht reproduzierbar, weil sie vom heutigen CRAN-Stand abhingen.
  - `install.packages()` meldet einen Fehlschlag nur als **Warnung**. Das Image wurde trotzdem gebaut, und die App scheiterte erst zur Laufzeit mit `there is no package called …`.
- **Lösung:**
  - Der Override entfällt, die Pakete kommen aus dem Snapshot des Images. Dazu kommt `options(timeout = 600)`.
  - Nach der Installation wird erneut geprüft, ob alle Pakete ladbar sind. Fehlt eines, bricht der Build mit `R packages could not be installed: <Pakete>` ab.
- **Ergebnis:**
  - Die Pakete sind auf das Snapshot-Datum festgelegt, passend dazu, dass auch der Commit gepinnt wird.
  - Die Builds sind etwa 5-mal schneller (Median 7 statt 16 s).
  - Fehlende Pakete erscheinen als Build-Fehler mit Namen.
  - Keine zusätzliche App läuft erfolgreich: Die `ctmm`- und `move`-Apps kommen jetzt über `library()` hinaus, scheitern dann aber an ihrer eigenen Logik (Abschnitt 5.3).
- **Code:** `generators.py` (`generate_dockerfile_content`)

### C. `appspec.json` ohne `settings`

- **Problem:** Der Packager lehnte eine `appspec.json` ohne `settings`-Schlüssel ab. Apps ohne Einstellungen lassen den Schlüssel aber legitim weg. Betroffen waren 4 Apps.
- **Lösung:** `settings` ist optional (leere Liste). Abgelehnt wird nur noch eine `appspec.json`, die kein JSON-Objekt ist.
- **Ergebnis:** Alle 4 Apps lassen sich paketieren. `pretty-units` läuft erfolgreich, die drei `ctmmMoveApp_*` scheitern zur Laufzeit am Datenmodell.
- **Code:** `github.py` (`fetch_repo`)

---

## 5. Warum die übrigen 60 Apps nicht laufen

Die Zuordnung basiert auf der Fehlermeldung jeder App (`summary.md`, Abschnitt „Failures“). Die Kategorien in 5.3 sind aus den Meldungen abgeleitet und nicht für jede App einzeln im Code nachvollzogen.

| Ursache | Apps | Verantwortung |
| --- | ---: | --- |
| `appspec.json` ist kein gültiges JSON | 10 | Repository |
| R-Paket nicht mehr auf CRAN | 4 | Repository (veraltete Abhängigkeit) |
| Binärpaket braucht fehlende Systembibliothek (`keyring`) | 3 | Grenze des Packagers |
| Abhängigkeit nicht in `appspec.json` deklariert | 3 | Repository |
| Datei-Setting bzw. nicht existierende SDK-Funktion `getAppFilePath()` | 4 | Grenze des Packagers / Repository |
| Erwartet altes Datenmodell (`MoveStack`, `telemetry`) statt `move2` | 21 | Testbedingung / App |
| Setting ohne sinnvollen Default bzw. fehlende Eingabe | 7 | Testbedingung |
| Braucht Zugangsdaten oder Internet | 2 | Testbedingung |
| Sonstige Fehler in der App | 6 | App |
| **gesamt** | **60** | |

### 5.1 Ungültige `appspec.json` (10, Paketieren)

`Add_Elevation`, `cloud-provider-download`, `Convert-Times-1`, `Daily-Rest-Sites`, `KML-output`, `move2TOtelemetry`, `moveStack2telemetry`, `Speed-Direction-Plots`, `Split-by-Time-Interval`, `stopovers`.

Meist ist es ein Komma nach dem letzten Element einer Liste oder eines Objekts (`},\n]`), was JSON nach RFC 8259 verbietet. Der R-Parser von MoveApps (`jsonlite`) ist nachsichtiger, deshalb fällt das dort nicht auf. Ein nachsichtiger Parser im Packager wurde bewusst nicht eingebaut: Er würde Dateien akzeptieren, die nicht dem Format entsprechen.

### 5.2 Abhängigkeiten (10)

- **Nicht mehr auf CRAN (4, Build):**
  - `rgeos` und `maptools` (`Nest-Use-Radius`, `RoostSites`) wurden am 16.10.2023 auf Wunsch des Maintainers entfernt.
  - `moveVis` (`animation-moveVis`) wurde am 11.07.2023 entfernt.
  - `nestR` (`Nest-Detection`) gibt es nicht auf CRAN.

  Die Apps hängen von Paketen ab, die nicht mehr gepflegt werden. Seit B scheitern sie beim Build und nennen das Paket.
- **`keyring` braucht `libsecret` (3, Build):** `Movebank-Loc-move2`, `Movebank_NonLoc`, `multistudy_movebank_locations`.
  - Das Binärpaket `keyring` aus dem Snapshot ist gegen `libsecret` gelinkt, und `libsecret-1.so.0` fehlt im Wrapper-Image. Aus dem Quellcode kompiliert, wie vor B, kommt `keyring` ohne `libsecret` aus.
  - Das ist die Kehrseite von Binärpaketen: Sie setzen die Systembibliotheken voraus, gegen die sie gebaut wurden.
  - Die Apps sind ohnehin Datenquellen, die Movebank-Zugangsdaten und Internet brauchen. Vor B sind sie zur Laufzeit gescheitert bzw. in den Timeout gelaufen. An der Erfolgszahl ändert sich also nichts.
  - **Bewusst nicht behoben.** Die allgemeine Lösung wäre ein Rückfall auf die Installation aus dem Quellcode (aus demselben Snapshot), wenn ein Binärpaket nicht ladbar ist. Eine einzelne Systembibliothek nachzurüsten wäre dagegen eine Sonderbehandlung.
- **Nicht deklariert (3, Laufzeit):**
  - `CTMM_Type_Example` (`suncalc`)
  - `select-year` (`move`, hat gar keine Dependencies in der `appspec.json`)
  - `Y2Y-Road-Interaction-BaBA` (`BaBA`)

  Das Paket wird in `RFunction.R` geladen, steht aber nicht in der `appspec.json`. Der Packager kann nur installieren, was deklariert ist. Auf MoveApps fällt das vermutlich nicht auf, weil dort andere Pakete vorinstalliert sind.

### 5.3 Altes Datenmodell (21, Laufzeit)

Ein großer Teil der Apps stammt aus der Zeit vor `move2` und ruft Methoden des Pakets `move` auf, die es für `move2`-Objekte nicht gibt. Beispiele: `timestamps()`, `idData()`, `namesIndiv()`, `extent()`, `angle()`, `timeLag()`, `split()`, Slot-Zugriff `data@timestamps`. Einige ctmm-Apps erwarten ein `telemetry`-Objekt.

Betroffen sind: `ColoringLocationsAnnotateCtmm`, `ctmmMoveApp_akdepop`, `ctmmMoveApp_modelselection`, `ctmmMoveApp_speeddistance`, `DirectionOfMovement`, `Distance_BetweenLocations`, `Filter-by-IdData`, `Filter-last-x-days`, `Filter-last-x-locations`, `FilterData-by-IndivTime`, `FilterData-bySpace`, `Flight-Speed-Estimation`, `LDA_carcass_spec`, `moveStack-to-move2_loc`, `Natural_Earth_Annotation`, `poc-lage-files`, `segment-by-speed-artefact`, `SegmentData-bySpeed`, `telemetry2moveStack`, `TimeLag_BetweenLocations`, `TurningAngles_BetweenLocations`.

Auf MoveApps deklariert jede App ihren Eingabetyp (`MoveStack`, `move2_loc`, `telemetry`, …). Die Plattform reicht ihr nur passende Daten weiter. Diese Typangabe steht aber **nicht** in `appspec.json`, sondern nur in der Plattform. Der Packager kann sie deshalb nicht übernehmen, und die Evaluation gibt allen Apps denselben `move2`-Datensatz. Diese Fehlschläge zeigen also vor allem, dass die Apps einen anderen Eingabetyp erwarten, und kaum Schwächen des Packagers. Mit einem passenden Datensatz pro Eingabetyp liefe ein Teil davon vermutlich.

### 5.4 Datei-Settings und `getAppFilePath()` (4, Laufzeit)

`app-setting-showcase`, `blank_R_template`, `Road_Intersection_fromFile`, `Y2Y_road_interaction` rufen `getAppFilePath()` auf. Diese Funktion gibt es im öffentlichen MoveApps-SDK nicht: Weder die Version 1.0.1 im Wrapper-Image noch die aktuelle 1.2.0 auf GitHub enthält sie, dort heißt die Funktion `getAuxiliaryFilePath()`.

Grundsätzlich kann der Packager Datei-Settings (`USER_FILE`/`LOCAL_FILE`) noch nicht abbilden, aus zwei Gründen:

- **Kein Datei-Input im CWL:** Sie werden als `string` in die CWL übernommen, ein `File` kann also nicht übergeben werden. Das SDK erwartet die Datei unter `$USER_APP_FILE_HOME_DIR/uploaded-app-files/<settingId>/`.
- **Fallback-Dateien fehlen im Image:** Die Dateien, die der Entwickler als Fallback mitliefert (`provided-app-files/<settingId>/`), landen nicht im Image der App.

Von den 8 Apps mit Datei-Settings laufen 2 trotzdem, weil die Datei optional ist (`Point-Cluster-Detection`, `plot_on_costum_basemap`). Bei den übrigen 6 ist die fehlende Datei nur bei einem Teil die Ursache. Die 4 oben scheitern an `getAppFilePath()`, `group_proximity` an einem Syntaxfehler in seiner eigenen `RFunction.R`, `Upload-File-from-Local` an der fehlenden Datei.

### 5.5 Testbedingungen (9, Laufzeit)

- **Setting ohne Default bzw. fehlende Eingabe (7):** `Daily-Proportions`, `date-range`, `DistanceMoved`, `Filter-Unrealistic-Values`, `rds-2-csv-time`, `Upload-File-from-Local`, `write-shapefile`. Die App braucht eine Nutzerentscheidung, z. B. „Please select an option in the setting …“, oder eine Spalte bzw. Datei, die der Testdatensatz nicht hat.
- **Zugangsdaten bzw. Internet (2):** `movebank-download` (Movebank-Login), `OSM-Data` (Overpass-API). CWL startet Container mit `--net=none`, und Zugangsdaten gibt es im Test nicht.

### 5.6 Sonstige Fehler in der App (6, Laufzeit)

`group_proximity` (Syntaxfehler in `RFunction.R`), `link-r-python` (definiert kein `rFunction`), `Add_Corine_Landcover2018`, `Mortality_by_Activity_Sensor`, `dynBrownianBridge`, `telemetryTOmove2`. Die Fehler entstehen in der Logik der App, mit den Testdaten bzw. den Defaults.

---

## 6. Einordnung

- **Paketieren gelingt bei 88,6 %:** Alle restlichen Fehlschläge in dieser Stufe sind ungültige `appspec.json`-Dateien in den Repositories.
- **Bauen gelingt bei 80,7 %:** Die 7 Build-Fehler gehen auf Abhängigkeiten zurück, die nicht mehr verfügbar sind (4), und auf eine Systembibliothek, die für ein Binärpaket fehlt (3).
- **Laufen gelingt bei 31,8 %:** Die größte Gruppe der Fehlschläge (21 von 43) liegt am Eingabetyp. Die Apps erwarten `MoveStack` oder `telemetry`, getestet wurde einheitlich mit `move2`. Grenzen des Packagers im engeren Sinn sind nur die Datei-Settings (Abschnitt 5.4) und die `keyring`-Bibliothek (5.2).

Rechnet man die Fälle heraus, für die das Repository verantwortlich ist (ungültige `appspec.json`, Pakete nicht mehr auf CRAN, nicht deklarierte Abhängigkeiten, nicht existierende SDK-Funktion: 21 Apps), laufen 28 von 67 Apps (41,8 %). Der Rest scheitert überwiegend am Eingabetyp bzw. an den Testbedingungen.

## 7. Grenzen der Methode

- **Ein Datensatz für alle Apps:** Der Eingabetyp der Apps ist nicht bekannt (Abschnitt 5.3).
- **Nur Defaults:** Settings ohne Default bleiben `null`, es gibt keine Nutzerdateien, keine Zugangsdaten und kein Netzwerk im Container.
- **Erfolg ist technisch definiert:** Eine `output.rds` existiert. Ob ihr Inhalt fachlich stimmt, wird nicht geprüft.
- **Momentaufnahme:**
  - Die Repositories wurden auf dem jeweils aktuellen Commit des Default-Branches gemessen.
  - Die R-Pakete stammen aus dem P3M-Snapshot vom 30.10.2025.
  - Das Wrapper-Image ist `ghcr.io/distr0hopper/moveapps-r-wrapper:r4.5.1-1`.
- **Archivierte Repositories und Forks sind mitgezählt** (7 bzw. 4 der 88 Apps). Sie sind in `results.csv` markiert.

## 8. Ausblick

- **Datei-Settings:** als `File?` in die CWL übernehmen, per `InitialWorkDirRequirement` unter `uploaded-app-files/<id>/` bereitstellen und die `provided-app-files` aus dem Repository mit ins Image kopieren.
- **Eingabetyp:** von der MoveApps-Plattform beziehen (er steht nicht in `appspec.json`), in der CWL als Format des Eingangs-Ports hinterlegen und in der Evaluation pro Typ einen passenden Datensatz verwenden.
- **`renv.lock` der Repositories auswerten** (62 von 88 Apps haben eine): Sie enthält exakte Versionen und auch GitHub-Quellen, z. B. `moveVis`. Ausgerechnet die alten Apps mit verschwundenen Abhängigkeiten haben aber meist keine.
- **Rückfall auf die Installation aus dem Quellcode,** wenn ein Binärpaket wegen fehlender Systembibliotheken nicht ladbar ist (Abschnitt 5.2).

## 9. Reproduktion

```bash
cd automated-packaging && source .venv/bin/activate   # Packager + cwltool
export GITHUB_TOKEN=ghp_...                           # ~5 API-Aufrufe pro App
python evaluation/evaluate_movestore.py --jobs 2      # alle 135 Repositories
python evaluation/evaluate_movestore.py --resume      # nach einem Abbruch fortsetzen
python evaluation/evaluate_movestore.py --only RemoveOutliers   # einzelne Apps
```
