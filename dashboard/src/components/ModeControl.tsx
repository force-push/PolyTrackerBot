/**
 * Mode control: switch between dry_run, demo, live
 */

import React from 'react';
import { motion } from 'framer-motion';
import { ExecutionMode } from '../types';

interface ModeControlProps {
  currentMode: ExecutionMode;
  onModeChange: (mode: ExecutionMode) => void;
  isLocked?: boolean;
  apiBaseUrl?: string;
}

export const ModeControl: React.FC<ModeControlProps> = ({
  currentMode,
  onModeChange,
  isLocked = false,
  apiBaseUrl = 'http://localhost:8000'
}) => {
  const [isChanging, setIsChanging] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const modes: { mode: ExecutionMode; label: string; description: string }[] = [
    { mode: ExecutionMode.DRY_RUN, label: 'Dry Run', description: 'Logging only, no orders' },
    { mode: ExecutionMode.DEMO, label: 'Demo', description: 'Paper trading at live prices' },
    { mode: ExecutionMode.LIVE, label: 'Live', description: 'Real money trading' },
  ];

  const handleModeSwitch = async (mode: ExecutionMode) => {
    setIsChanging(true);
    setMessage(null);
    setError(null);

    try {
      const endpoint = mode === ExecutionMode.LIVE ? '/api/mode/set-confirmed' : '/api/mode/set';
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode }),
      });

      const data = await response.json();

      if (data.success) {
        setMessage(`✅ ${data.message}`);
        onModeChange(mode);
        setTimeout(() => setMessage(null), 5000);
      } else {
        setError(data.error || 'Failed to change mode');
      }
    } catch (err) {
      setError(`Failed to connect to API: ${err}`);
    } finally {
      setIsChanging(false);
    }
  };

  const getModeColor = (mode: ExecutionMode) => {
    switch (mode) {
      case ExecutionMode.DRY_RUN:
        return 'from-yellow-500/20 to-yellow-500/5 border-yellow-500/30';
      case ExecutionMode.DEMO:
        return 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/30';
      case ExecutionMode.LIVE:
        return 'from-red-500/20 to-red-500/5 border-red-500/30';
    }
  };

  return (
    <div className="space-y-4 font-mono">
      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500">Execution Mode</h3>

      <div className="space-y-2">
        {modes.map(({ mode, label, description }) => (
          <motion.button
            key={mode}
            onClick={() => !isLocked && !isChanging && handleModeSwitch(mode)}
            disabled={isLocked || isChanging}
            whileHover={!isLocked && !isChanging ? { scale: 1.02 } : {}}
            whileTap={!isLocked && !isChanging ? { scale: 0.98 } : {}}
            className={`
              w-full p-3 border-2 rounded-sm transition-all text-left
              ${currentMode === mode ? `bg-gradient-to-r ${getModeColor(mode)} border-current` : 'bg-zinc-900 border-gray-700 opacity-60 hover:opacity-80'}
              ${isLocked ? 'cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-bold uppercase text-sm">{label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{description}</div>
              </div>
              {currentMode === mode && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="w-3 h-3 rounded-full bg-current"
                />
              )}
            </div>
          </motion.button>
        ))}
      </div>

      {message && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-xs text-green-400 bg-green-500/10 p-2 border border-green-500/30 rounded-sm"
        >
          {message}
        </motion.div>
      )}

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-xs text-red-400 bg-red-500/10 p-2 border border-red-500/30 rounded-sm"
        >
          ❌ {error}
        </motion.div>
      )}

      {isChanging && (
        <div className="text-xs text-cyan-400 bg-cyan-500/10 p-2 border border-cyan-500/30 rounded-sm">
          Changing mode... Bot will use new mode on next restart.
        </div>
      )}

      {isLocked && (
        <div className="text-xs text-yellow-400 bg-yellow-500/10 p-2 border border-yellow-500/30 rounded-sm">
          Mode locked while running. Stop bot to change.
        </div>
      )}

      <div className="text-xs text-gray-600 mt-4 p-3 bg-zinc-900 border border-gray-700 rounded-sm">
        <strong>Warning:</strong> Live mode executes real trades on Polymarket. Only enable after thorough demo validation.
      </div>
    </div>
  );
};
