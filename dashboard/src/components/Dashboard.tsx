/**
 * Main dashboard layout
 * Brutalist trading UI: raw data, precise typography, selective neon accents
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useDashboardStore } from '../store';
import { ExecutionMode, WebSocketMessage } from '../types';
import { SignalFeed } from './SignalFeed';
import { ExecutionPanel } from './ExecutionPanel';
import { RiskMonitor } from './RiskMonitor';
import { ModeControl } from './ModeControl';

export const Dashboard: React.FC = () => {
  const store = useDashboardStore();
  const [isConnected, setIsConnected] = useState(false);
  const [wsError, setWsError] = useState<string | null>(null);

  // Connect to WebSocket in real implementation
  useEffect(() => {
    // In production, connect to backend WebSocket
    // const ws = new WebSocket('ws://localhost:8000/ws/dashboard');
    // Mock connection for now
    setIsConnected(true);
  }, []);

  const handleModeChange = (mode: ExecutionMode) => {
    store.updateConfig({ executionMode: mode });
    // In production, send mode change to backend
  };

  return (
    <div className="min-h-screen bg-black text-white font-mono">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gradient-to-r from-black via-black to-gray-900/20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tighter">POLYTRACKER</h1>
              <p className="text-xs text-gray-500 mt-1">Real-time whale signal execution engine</p>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-cyan-400 animate-pulse' : 'bg-red-400'}`} />
                <span className="text-xs text-gray-500">{isConnected ? 'Connected' : 'Disconnected'}</span>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold text-white">{new Date().toLocaleTimeString()}</div>
              </div>
            </div>
          </div>

          {/* Status Bar */}
          <motion.div className="text-xs text-gray-400 space-y-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div>
              Mode: <span className="text-cyan-400 font-semibold">{store.config.executionMode.toUpperCase()}</span> •{' '}
              {store.signals.length} signals • {store.orders.length} orders • {store.positions.length} positions
            </div>
            <div>
              Daily P&L: <span className={store.stats.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                ${store.stats.totalPnl.toFixed(2)}
              </span>{' '}
              • Win Rate: <span className="text-cyan-300">{(store.stats.winRate * 100).toFixed(1)}%</span> • Risk Events:{' '}
              <span className="text-yellow-400">{store.stats.riskEvents}</span>
            </div>
          </motion.div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-12 gap-6">
          {/* Left Column: Signals & Monitoring */}
          <div className="col-span-12 lg:col-span-7 space-y-6">
            {/* Signal Feed */}
            <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <div className="bg-gradient-to-br from-black via-zinc-900 to-black border border-gray-800 rounded-sm p-6">
                <SignalFeed signals={store.signals} />
              </div>
            </motion.section>

            {/* Execution Panel */}
            <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <div className="bg-gradient-to-br from-black via-zinc-900 to-black border border-gray-800 rounded-sm p-6">
                <ExecutionPanel orders={store.orders} positions={store.positions} mode={store.config.executionMode} />
              </div>
            </motion.section>
          </div>

          {/* Right Column: Controls & Risk */}
          <div className="col-span-12 lg:col-span-5 space-y-6">
            {/* Mode Control */}
            <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
              <div className="bg-gradient-to-br from-black via-zinc-900 to-black border border-gray-800 rounded-sm p-6">
                <ModeControl currentMode={store.config.executionMode} onModeChange={handleModeChange} isLocked={false} />
              </div>
            </motion.section>

            {/* Risk Monitor */}
            <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
              <div className="bg-gradient-to-br from-black via-zinc-900 to-black border border-gray-800 rounded-sm p-6">
                <RiskMonitor events={store.riskEvents} />
              </div>
            </motion.section>

            {/* Quick Stats */}
            <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-zinc-900 border border-gray-700 rounded-sm p-3">
                  <div className="text-xs text-gray-500 mb-1">Max Daily Loss</div>
                  <div className="text-lg font-bold text-white">${store.config.maxDailyLoss}</div>
                </div>
                <div className="bg-zinc-900 border border-gray-700 rounded-sm p-3">
                  <div className="text-xs text-gray-500 mb-1">Max Position</div>
                  <div className="text-lg font-bold text-white">${store.config.maxPositionSize}</div>
                </div>
              </div>
            </motion.section>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 bg-black mt-12 py-4 text-center text-xs text-gray-600">
        <div>PolyTrackerBot Dashboard • Phase {isConnected ? '2' : 'offline'}</div>
      </footer>
    </div>
  );
};
