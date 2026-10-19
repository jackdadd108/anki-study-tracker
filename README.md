# Anki Study Tracker

A local MCQ practice app built with Python and vanilla JavaScript. Python 3 is the only runtime dependency. Node.js is optional for JavaScript checks.

## Run

```sh
python3 run.py
```

Open http://127.0.0.1:8765/. On macOS, you can also double-click `Start.command`. Keep the terminal running. If your installed tracker already uses port 8765, close that instance before running a separate checkout.

The launcher creates an empty local `data.json` only if none exists. Import an Anki `.apkg` deck or restore a JSON backup in the app. Newer compressed Anki packages may need to be exported with **Support older Anki versions** enabled. Imported media is stored locally under `static/media`.

## Features

- Radio-button MCQs, answer explanations and imported images. Valid options turn green; an incorrect selected option turns red. For a question with multiple valid answers, choosing any one valid option earns full credit.
- Previous/next navigation, remaining-question count, retry queues, and saved attempt history.
- Sticky daily progress, editable schedule, and Nepal-midnight daily rollover without deleting history.
- Micro targets with question counts in steps of 5, editable minutes, countdown, and automatic restoration.
- Accuracy and exam marks: correct +1, wrong −0.25. The dashboard exam percentage divides net marks by attempted questions, including retries.
- Answer-only Mac speech using installed system voices; playback speed options 1×, 1.1× and 1.2×.
- Keyboard shortcuts: **E** opens the matching Anki note, **R** reads/stops the revealed answer, **Space** saves and advances after reveal, and **Shift+Space** reads/stops. Text entry and open dialogs suppress shortcuts.
- Local JSON backup/restore and wrong-answer CSV export.

## Optional Anki Desktop integration

Keep Anki Desktop open with AnkiConnect configured on `127.0.0.1:8766` (the tracker itself uses 8765). Sync Anki applies tracker tags and sends matched scored attempts to Anki review history. New answers use Good for correct and Again for wrong and can change Anki scheduling. The local `anki-reviews.json` journal prevents duplicate submissions. Ambiguous matches are skipped.

Edit in Anki opens the matched note in Anki's browser. Editing there does not automatically pull the changed content into this tracker.

## What this repository backs up

This repository contains application code and tests. It intentionally excludes decks, question banks, imported pictures, attempt history, Anki profiles, logs, and credentials. It is **not** a backup of study progress.

To preserve the installed app's study data separately, keep a private copy of its `data.json`, `anki-reviews.json`, and `static/media/` together while the app is closed. The in-app JSON backup does not embed picture files. Do not replace live data with an older code snapshot.

## Checks

```sh
python3 tests/completion_test.py
python3 tests/multi_answer_test.py
python3 tests/media_test.py
python3 tests/review_sync_test.py
node tests/daily.test.cjs
node tests/multi-answer.test.cjs
node tests/micro.test.cjs
```
