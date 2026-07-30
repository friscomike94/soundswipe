# SoundSwipe Ableton DNA Bridge

Local-only companion for the `Ableton DNA` tab in SoundSwipe.

## What it does

- Reads the existing Ableton Core Library preview OGG files.
- Serves 2,563 previews to an iPhone on the same Wi-Fi.
- Keeps raw preview audio on the Mac.
- Sends only ratings to the existing SoundSwipe Supabase database.
- Exposes 1,994 Device/Rack sources for Stage 1 and 569 Groove/MIDI items for Stage 3.

## Automatic connection

1. Double-click `Install Automatic Connection.command` once.
2. The Bridge will start automatically at future Mac logins.
3. Scan the QR once on the iPhone and choose **Add to Home Screen**.
4. From then on, opening the SoundSwipe icon reconnects automatically through the Mac's stable `.local` address.

The Mac and iPhone must be on the same Wi-Fi, and the Mac must be awake.

## Manual start

Double-click `Start Ableton DNA.command`, or run:

```bash
cd ~/Documents/AbletonAIExperiment/SoundSwipeAbletonBridge
python3 ableton_bridge.py --port 8877
```

The Mac browser opens automatically. Open the Ableton tab and scan its QR code with the iPhone.

## Required local file

`data/ableton_core_library_catalog.json`

This catalog is generated from the installed Ableton Core Library. Raw OGG files are never copied into the GitHub repository.

## Stage architecture

1. **Source DNA**: stream and rate 1,994 Devices/Racks.
2. **Effect DNA**: Mac renders selected sources through controlled Ableton effect chains.
3. **Gesture DNA**: test 569 Grooves/MIDI Clips and applied gesture variants.
4. **Context DNA**: render controlled 8-bar micro-arrangements.
5. **Suno Transfer**: test whether validated capsules survive Suno conditioning.
6. **Production DNA**: lock Source, Effect, Gesture, Context, Anti-DNA, and Suno recipes.

Stages 2-4 use the same bridge. The phone only plays and rates; the Mac/Ableton side creates and serves rendered test files.
