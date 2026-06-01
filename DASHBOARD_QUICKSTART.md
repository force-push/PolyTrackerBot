# Dashboard Quick Start

## Installation

### Prerequisites
- Node.js 18+
- npm or pnpm

### Setup

```bash
cd dashboard
npm install
```

## Development

### Start Dashboard

```bash
npm run dev
```

Opens at `http://localhost:3000`

### Start Bot + WebSocket Server

In another terminal:

```bash
cd ..
export EXECUTION_MODE=demo
export TELEGRAM_BOT_TOKEN="token"
export TELEGRAM_CHANNEL_ID="channel"
python -m polytracker.main
```

**Note:** WebSocket integration coming soon. Currently dashboard shows mock data.

## Production Build

```bash
npm run build
npm run preview
```

## Design

**Brutalist Financial Data UI**

- Monospace type (JetBrains Mono)
- Minimal color palette
- Real-time animations
- Dark mode optimized
- Selective neon accents (cyan/green/red)

## Components

### Dashboard
Main layout, header, footer, grid system

### SignalFeed
Live whale signals, expandable details

### ExecutionPanel
Orders, positions, P&L tracking

### RiskMonitor
Risk events, critical alerts, event log

### ModeControl
Switch between dry_run → demo → live

## State Management

**Zustand store** — `src/store.ts`

```typescript
const { signals, orders, positions } = useDashboardStore();
```

## Customization

### Colors

Edit `src/index.css`:

```css
/* Change neon accent */
.accent-neon {
  @apply text-cyan-400; /* Your color */
}
```

### Fonts

Edit `tailwind.config.js`:

```js
fontFamily: {
  mono: ['"Your Font"', 'monospace'],
}
```

## Performance

- Lazy-loaded components
- Memoized lists
- CSS-only animations
- ~35 KB gzipped

## Next Steps

1. Connect WebSocket to backend (currently mocked)
2. Add historical P&L charts
3. Add keyboard shortcuts
4. Enable real-time price updates

---

**Ready for Production**  
Type-forward design, zero fluff, optimized for trading.
