# ElderGuard AI — Fall Detection and Elder Care

A local-first demonstration of **Track 2: Fall Detection and Elder Care**. Browser-based MediaPipe pose estimation checks for a rapid posture transition followed by a sustained low horizontal posture. It records suspected events to FastAPI/SQLite and shows alerts and acknowledgements on the caregiver dashboard. **Not a certified safety device. Do not depend on it for emergency response.**

## Run on Windows (PowerShell)

```powershell
cd ElderGuardAI
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000**. Allow camera access and click **Start AI Camera**. Camera works on localhost or HTTPS. The first run needs internet to download MediaPipe JavaScript and its model. Video processing happens locally in the browser; raw frames are not sent to FastAPI. Keep the browser tab open for monitoring.

For automated tests: run `python tests/test_api.py` (zero extra dependencies required). Or install test runner: `pip install -r requirements-dev.txt` then `python -m pytest -q`.

## Features

- Browser camera + MediaPipe pose landmark estimation; temporal heuristic to flag suspected falls, with cooldown
- Incident records in SQLite, acknowledge action, counts and CSV export
- Manual SOS and a **clearly labelled simulation** button
- Caregiver contact saved in the browser, with click-to-call link; optional browser notifications
- API at `/docs`, integration contract and forwarding bridge in `pipegen/`

## PipeGen requirement

The project includes a **PipeGen integration contract and JSONL bridge**, but **does not include a PipeGen-generated or hardware-optimised inference runtime**. Follow `pipegen/README.md` to generate one using CraftifAI, validate it on your hardware and connect its actual JSON events. Never claim PipeGen inference was executed until this is done.

## Important limits

Pose-based fall detection is heuristic and may miss falls or confuse sitting, crouching, lying down or occlusion. No SMS, WhatsApp, phone calls or emergency service dispatch is automatic. The server is unauthenticated: run on localhost only, not a public network. It does not store video. Browser notifications work only when permitted. Test with consenting adults and staged movements, not real dangerous falls.

## File guide

`main.py`: API/database; `static/index.html`: dashboard; `static/app.js`: camera + API; `static/detection.js`: fall heuristic; `pipegen/bridge.py`: JSONL event forwarder; `tests/`: automated API and bridge tests.
