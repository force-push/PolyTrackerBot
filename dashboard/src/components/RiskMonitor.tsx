/**
 * Risk monitoring: live alerts, constraint breaches, event log
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RiskEvent } from '../types';

interface RiskMonitorProps {
  events: RiskEvent[];
}

export const RiskMonitor: React.FC<RiskMonitorProps> = ({ events }) => {
  const criticalEvents = events.filter((e) => e.severity === 'critical');
  const hasActiveCriticals = criticalEvents.length > 0;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/50 text-red-400';
      case 'warning':
        return 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400';
      default:
        return 'bg-gray-900 border-gray-700';
    }
  };

  return (
    <div className="space-y-4 font-mono text-sm">
      {/* Critical Alert Banner */}
      <AnimatePresence>
        {hasActiveCriticals && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-3 bg-red-500/20 border border-red-500/50 rounded-sm"
          >
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              <span className="text-red-400 font-bold uppercase tracking-widest text-xs">
                {criticalEvents.length} Critical Event{criticalEvents.length !== 1 ? 's' : ''}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Risk Events Log */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">Risk Events</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          <AnimatePresence mode="popLayout">
            {events.slice(0, 15).map((event) => (
              <motion.div
                key={event.id}
                layout
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className={`p-2 border border-l-2 text-xs rounded-sm ${getSeverityColor(event.severity)}`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-semibold uppercase tracking-wider">{event.type}</span>
                  <span className="text-xs text-gray-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="text-gray-300 mb-1">{event.description}</div>
                {event.actionTaken && (
                  <div className="text-gray-600 italic text-xs">→ {event.actionTaken}</div>
                )}
                {(event.currentValue !== undefined || event.limitValue !== undefined) && (
                  <div className="mt-1 text-gray-600">
                    current: <span className="text-white">{event.currentValue?.toFixed(2)}</span> / limit:{' '}
                    <span className="text-white">{event.limitValue?.toFixed(2)}</span>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {events.length === 0 && (
            <div className="text-center py-8 text-gray-600">
              <div className="text-xs">no risk events</div>
            </div>
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-zinc-900 p-2 border border-gray-700 rounded-sm">
          <div className="text-gray-500">Total Events</div>
          <div className="text-lg font-bold text-white">{events.length}</div>
        </div>
        <div className="bg-red-500/5 p-2 border border-red-500/30 rounded-sm">
          <div className="text-red-400">Critical</div>
          <div className="text-lg font-bold text-red-400">{criticalEvents.length}</div>
        </div>
        <div className="bg-yellow-500/5 p-2 border border-yellow-500/30 rounded-sm">
          <div className="text-yellow-400">Warnings</div>
          <div className="text-lg font-bold text-yellow-400">{events.filter((e) => e.severity === 'warning').length}</div>
        </div>
      </div>
    </div>
  );
};
