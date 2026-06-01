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
}

export const ModeControl: React.FC<ModeControlProps> = ({ currentMode, onModeChange, isLocked = false }) => {
  const modes: { mode: ExecutionMode; label: string; description: string }[] = [
    { mode: ExecutionMode.DRY_RUN, label: 'Dry Run', description: 'Logging only, no orders' },
    { mode: ExecutionMode.DEMO, label: 'Demo', description: 'Paper trading at live prices' },
    { mode: ExecutionMode.LIVE, label: 'Live', description: 'Real money trading' },
  ];

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
            onClick={() => !isLocked && onModeChange(mode)}
            disabled={isLocked}
            whileHover={!isLocked ? { scale: 1.02 } : {}}
            whileTap={!isLocked ? { scale: 0.98 } : {}}
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
