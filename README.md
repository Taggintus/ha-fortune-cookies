# Fortunes für Home Assistant

Ein Spruch pro Tag aus klassischen Unix-Fortune-Sammlungen, in wählbarer Sprache (Deutsch, English, Français, Español, Italiano)

## Entitäten

|Entität|Zweck|
|-|-|
|Sensor „Spruch“|Status = Spruch (max. 255 Zeichen), Attribut `fortune` = voller Text|
|Button „Neuer Spruch“|zufälliger Spruch in der gewählten Sprache|
|Select „Sprache“|Sprache umschalten (wird gespeichert, fehlende Sprüche werden geladen)|

Der Spruch des Tages ist pro Tag und Sprache fest und wechselt um 00:00:10 Uhr (Zeitzone von Home Assistant). Ein per Knopf gezogener Spruch gilt bis zum nächsten Tageswechsel oder Neustart.

## Installation über HACS

1. HACS öffnen → ⋮ → **Benutzerdefinierte Repositories**
2. URL dieses Repositories eintragen, Kategorie **Integration**
3. „Fortunes“ herunterladen und Home Assistant neu starten
4. Einstellungen → Geräte \& Dienste → Integration hinzufügen → **Fortunes**

Voraussetzungen: Home Assistant 2024.8 oder neuer; beim ersten Einrichten einer Sprache Internetzugang.

## Woher kommen die Sprüche? (Lizenzen)

Dieses Repository enthält **keine Sprüche**. Gibt es für eine Sprache keine lokalen Dateien, lädt die Integration einmalig das passende Debian-Paket (`fortunes-de`, `fortunes`, `fortunes-fr`, `fortunes-es`, `fortunes-it`) von `deb.debian.org` (Ausweich-Spiegel: `ftp.de.debian.org`, `mirrors.mit.edu`) auf **deine** Home-Assistant-Instanz und entpackt nur die Fortune-Dateien nach `/config/fortunes/<sprache>/`.

* Für `fortunes-de` gibt Debian GPL-2+ an (Copyright Andreas Tille). Das betrifft die Sammlung; ob jeder Einzelspruch von seinem Urheber freigegeben ist, geht daraus nicht hervor.
* Für die übrigen Sprachen sind die Lizenzen nicht geprüft. Sie stehen in `copyright` des jeweiligen Pakets (packages.debian.org).
* Beim englischen Paket werden die Dateien `songs-poems`, `ethnic`, `art` und `ascii-art` übersprungen, falls vorhanden. Ordner `off` (anstößige Sammlungen) und Indexdateien (`\*.dat`) werden nie entpackt.
* Das ist keine Rechtsberatung.

### Eigene oder manuell abgelegte Dateien

Lokale Dateien haben immer Vorrang, dann wird nichts geladen. Die Integration sucht pro Sprache der Reihe nach (erster Treffer gewinnt):

1. `/config/fortunes/<sprache>/` (rekursiv)
2. `/usr/share/games/fortunes/<sprache>/` (Debian/Ubuntu-Systeme)
3. nur Englisch: `/usr/share/games/fortunes/` (oberste Ebene)

Format: Einträge getrennt durch eine Zeile mit nur `%`; UTF-8 oder ISO-8859-1. Weitere Sprachen: in `const.py` (`LANGUAGES`) und `downloader.py` (`SOURCES`) eintragen und in beiden `translations/\*.json` einen Status-Namen ergänzen.

## Dashboard-Beispiel

```yaml
type: vertical-stack
cards:
  - type: markdown
    title: Spruch des Tages
    content: >
      {{ state\_attr('sensor.DEINE\_ENTITAET', 'fortune') | replace('\\n', '  \\n') }}
  - type: entities
    entities:
      - select.DEINE\_SPRACH\_ENTITAET
      - button.DEINE\_BUTTON\_ENTITAET
```

Entity-IDs findest du unter Einstellungen → Geräte \& Dienste → Fortunes.

## Automation-Beispiel (täglich per Benachrichtigung)

```yaml
triggers:
  - trigger: time
    at: "08:00:00"
actions:
  - action: notify.mobile\_app\_DEIN\_HANDY
    data:
      title: Spruch des Tages
      message: "{{ state\_attr('sensor.DEINE\_ENTITAET', 'fortune') }}"
```

