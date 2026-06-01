/**
 * Live signal feed component
 * Brutalist design: monospace type, raw data, minimal chrome
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Signal, ExecutionMode } from '../types';
import { useDashboardStore } from '../store';

interface SignalFeedProps {
  signals: Signal[];
}

export const SignalFeed: React.FC<SignalFeedProps> = ({ signals }) => {
  const { selectedSignalId, selectSignal } = useDashboardStore();

  const getModeColor = (mode: ExecutionMode) => {
    switch (mode) {
      case ExecutionMode.DRY_RUN:
        return 'text-yellow-400';
      case ExecutionMode.DEMO:
        return 'text-cyan-400';
      case ExecutionMode.LIVE:
        return 'text-red-400';
    }
  };

  const getAlertBg = (alertType: string) => {
    return alertType === 'high_conviction' ? 'bg-zinc-800 border-l-2 border-cyan-400' : 'bg-zinc-900 border-l-2 border-gray-700';
  };

  return (
    <div className="space-y-2 font-mono text-sm">
      <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">
        Live Signals
        <span className="ml-2 text-cyan-400">({signals.length})</span>
      </h2>

      <AnimatePresence mode="popLayout">
        {signals.slice(0, 20).map((signal) => (
          <motion.div
            key={signal.id}
            layout
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            onClick={() => selectSignal(selectedSignalId === signal.id ? null : signal.id)}
            className={`
              p-3 cursor-pointer transition-colors border-l-2
              ${getAlertBg(signal.alertType)}
              ${selectedSignalId === signal.id ? 'bg-zinc-700' : 'hover:bg-zinc-800'}
            `}
          >
            <div className="flex justify-between items-start mb-2">
              <div className="flex-1">
                <div className="text-xs text-gray-400 mb-1">
                  {new Date(signal.timestamp).toLocaleTimeString()}
                </div>
                <div className="text-white font-semibold leading-tight">{signal.market}</div>
              </div>
              <div className="text-right">
                <span className={`text-sm font-bold ${signal.direction === 'YES' ? 'text-green-400' : 'text-red-400'}`}>
                  {signal.direction}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs mb-2">
              <div>
                <span className="text-gray-500">whale</span>
                <br />
                <span className="text-cyan-300">
                  {signal.whaleAddress.slice(0, 6)}...{signal.whaleAddress.slice(-4)}
                </span>
              </div>
              <div>
                <span className="text-gray-500">score</span>
                <br />
                <span className="text-white">{signal.whaleScore.toFixed(1)}</span>
              </div>
              <div>
                <span className="text-gray-500">size</span>
                <br />
                <span className="text-white">${(signal.whaleSize / 1000).toFixed(1)}k</span>
              </div>
            </div>

            {selectedSignalId === signal.id && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-3 pt-3 border-t border-gray-700 text-xs"
              >
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-gray-500">strength</span>
                    <br />
                    <span className="text-yellow-400">{(signal.signalStrength * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <span className="text-gray-500">status</span>
                    <br />
                    <span className="text-white capitalize">{signal.status}</span>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {signals.length === 0 && (
        <div className="text-center py-8 text-gray-600">
          <div className="text-xs">waiting for signals...</div>
        </div>
      )}
    </div>
  );
};
