# Execution Mode Control API

## Overview
The dashboard can now control execution mode (DRY_RUN, DEMO, LIVE) via a REST API without manual .env editing.

## API Endpoints

### GET /api/mode/info
Get available modes and current configuration.

```bash
curl http://localhost:8000/api/mode/info
```

Response:
```json
{
  "current_mode": "DEMO",
  "available_modes": [
    {
      "mode": "DRY_RUN",
      "description": "Logging only, no orders",
      "money_risk": "None"
    },
    {
      "mode": "DEMO",
      "description": "Paper trading on demo account",
      "money_risk": "None (demo funds)"
    },
    {
      "mode": "LIVE",
      "description": "Real money trading",
      "money_risk": "REAL MONEY ⚠️"
    }
  ]
}
```

### GET /api/mode/current
Get current execution mode.

```bash
curl http://localhost:8000/api/mode/current
```

Response:
```json
{
  "mode": "DEMO"
}
```

### POST /api/mode/set
Change execution mode (use for DRY_RUN or DEMO).

```bash
curl -X POST http://localhost:8000/api/mode/set \
  -H "Content-Type: application/json" \
  -d '{"mode": "DEMO"}'
```

Response (success):
```json
{
  "success": true,
  "message": "Mode changed to DEMO. Bot will use new mode on next restart.",
  "previous_mode": "DRY_RUN",
  "new_mode": "DEMO",
  "requires_restart": true
}
```

Response (LIVE attempted without confirmation):
```json
{
  "success": false,
  "error": "LIVE mode requires explicit confirmation. Use set_mode_confirmed() instead.",
  "warning": "LIVE mode trades with REAL MONEY. This is irreversible."
}
```

### POST /api/mode/set-confirmed
Change execution mode with LIVE confirmation (use for LIVE only).

```bash
curl -X POST http://localhost:8000/api/mode/set-confirmed \
  -H "Content-Type: application/json" \
  -d '{"mode": "LIVE"}'
```

Response:
```json
{
  "success": true,
  "message": "Mode changed to LIVE. Bot will use new mode on next restart.",
  "previous_mode": "DEMO",
  "new_mode": "LIVE",
  "requires_restart": true
}
```

## Starting the API Server

The API server runs alongside the bot on port 8000.

### Option 1: Integrated (Recommended)
Modify `polytracker/main.py` to start the API server:

```python
from polytracker.api.server import start_api_server

# In main() function, alongside scheduler start:
asyncio.create_task(start_api_server(port=8000))
```

### Option 2: Standalone
```bash
cd ~/code/openclaw/projects/PolyTrackerBot
source venv/bin/activate
python -m polytracker.api.server
```

## Dashboard Integration

The ModeControl component now calls the API:

```typescript
// In ModeControl.tsx
const handleModeSwitch = async (mode: ExecutionMode) => {
  const response = await fetch('http://localhost:8000/api/mode/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  });
  
  const data = await response.json();
  if (data.success) {
    // Show success message
  }
};
```

## How It Works

1. **UI Click** — User clicks mode button in dashboard
2. **API Request** — Dashboard sends POST to `/api/mode/set` or `/api/mode/set-confirmed`
3. **File Update** — API updates EXECUTION_MODE in `.env`
4. **Response** — API returns success/error message
5. **Restart** — User restarts bot (or auto-restart logic)
6. **New Mode** — Bot reads updated .env and uses new mode

## Safety Features

### LIVE Mode Protection
- Requires explicit confirmation endpoint (`/api/mode/set-confirmed`)
- Dashboard prompts user with warning before calling confirmed endpoint
- Separate endpoint prevents accidental LIVE mode activation

### Validation
- Only accepts: DRY_RUN, DEMO, LIVE
- Returns error for invalid mode values

### Logging
- Mode changes logged to bot logs
- LIVE mode changes trigger warning message

## Workflow Example

### Switching to DEMO from DRY_RUN

```
User clicks "DEMO" button in dashboard
  ↓
ModeControl sends POST /api/mode/set with {"mode": "DEMO"}
  ↓
API validates mode ✓
  ↓
API updates .env: EXECUTION_MODE=DEMO
  ↓
API returns success response
  ↓
Dashboard shows "✅ Mode changed to DEMO"
  ↓
User restarts bot (or auto-restart triggered)
  ↓
Bot reads new .env value
  ↓
Bot now runs in DEMO mode (real orders on demo account)
```

## Logging Output

When mode changes via API:

```
✅ Execution mode changed: DRY_RUN → DEMO
📡 Mode control API server started on 127.0.0.1:8000
```

When LIVE mode is confirmed:

```
⚠️ SWITCHING TO LIVE MODE - REAL MONEY TRADING ENABLED
✅ Execution mode changed: DEMO → LIVE
```

## Dashboard UI Feedback

- **Success message** — Green banner with message, auto-hides after 5s
- **Error message** — Red banner showing what went wrong
- **Loading state** — Cyan banner "Changing mode..." while request pending
- **Button disabled** — While changing mode to prevent double-clicks

## File Locations

- API Server: `polytracker/api/server.py`
- Mode Controller: `polytracker/api/mode_control.py`
- Dashboard Component: `dashboard/src/components/ModeControl.tsx`
- Config: `.env` (updated by API)

## Troubleshooting

### "Failed to connect to API"
- Check API server is running on port 8000
- Verify bot is running: `pgrep -f polytracker`

### Mode change failed but no error
- Check API logs: `tail -f logs/polytracker.log | grep "mode\|Mode"`
- Verify .env file is writable: `ls -l .env`

### LIVE mode won't switch
- Use `/api/mode/set-confirmed` endpoint instead
- This is intentional safety restriction

---

**Status:** ✅ Production Ready  
**API Port:** 8000 (localhost)  
**CORS:** Enabled for dashboard access
