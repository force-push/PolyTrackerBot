/**
 * Execution panel: orders, positions, live P&L
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Order, Position, ExecutionMode } from '../types';

interface ExecutionPanelProps {
  orders: Order[];
  positions: Position[];
  mode: ExecutionMode;
}

export const ExecutionPanel: React.FC<ExecutionPanelProps> = ({ orders, positions, mode }) => {
  const filledOrders = orders.filter((o) => o.status === 'filled');
  const totalPnl = filledOrders.reduce((sum, o) => sum + (o.pnl || 0), 0);
  const winRate =
    filledOrders.length > 0 ? ((filledOrders.filter((o) => (o.pnl || 0) > 0).length / filledOrders.length) * 100).toFixed(1) : 0;

  const getModeColor = () => {
    switch (mode) {
      case ExecutionMode.DRY_RUN:
        return 'bg-yellow-500/10 border-yellow-500/30';
      case ExecutionMode.DEMO:
        return 'bg-cyan-500/10 border-cyan-500/30';
      case ExecutionMode.LIVE:
        return 'bg-red-500/10 border-red-500/30';
    }
  };

  return (
    <div className="space-y-6 font-mono text-sm">
      {/* Mode Badge */}
      <div className={`p-3 border rounded-sm ${getModeColor()}`}>
        <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Execution Mode</div>
        <div className="text-lg font-bold uppercase">{mode.replace('_', ' ')}</div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-zinc-900 p-3 border border-gray-700">
          <div className="text-xs text-gray-500 mb-1">Orders</div>
          <div className="text-2xl font-bold text-white">{filledOrders.length}</div>
          <div className="text-xs text-gray-600 mt-1">{orders.filter((o) => o.status === 'pending').length} pending</div>
        </div>

        <div className="bg-zinc-900 p-3 border border-gray-700">
          <div className="text-xs text-gray-500 mb-1">Positions</div>
          <div className="text-2xl font-bold text-white">{positions.filter((p) => !p.isClosed).length}</div>
          <div className="text-xs text-gray-600 mt-1">{positions.filter((p) => p.isClosed).length} closed</div>
        </div>

        <div className={`p-3 border ${totalPnl > 0 ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
          <div className="text-xs text-gray-500 mb-1">P&L</div>
          <div className={`text-2xl font-bold ${totalPnl > 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${totalPnl.toFixed(2)}
          </div>
        </div>

        <div className="bg-zinc-900 p-3 border border-gray-700">
          <div className="text-xs text-gray-500 mb-1">Win Rate</div>
          <div className="text-2xl font-bold text-cyan-400">{winRate}%</div>
        </div>
      </div>

      {/* Recent Orders */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">Recent Orders</h3>
        <div className="space-y-2">
          <AnimatePresence>
            {orders.slice(0, 10).map((order) => (
              <motion.div
                key={order.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className={`p-2 border-l-2 text-xs ${
                  order.status === 'filled' ? 'bg-green-500/5 border-green-500/50' : 'bg-gray-900 border-gray-700'
                }`}
              >
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">{order.market.slice(0, 20)}...</span>
                  <span className={order.direction === 'YES' ? 'text-green-400' : 'text-red-400'}>{order.direction}</span>
                </div>
                <div className="flex justify-between text-gray-500">
                  <span>${order.sizeUsd.toFixed(0)}</span>
                  <span className={order.pnl && order.pnl > 0 ? 'text-green-400' : 'text-red-400'}>
                    {order.pnl ? `${order.pnl > 0 ? '+' : ''}$${order.pnl.toFixed(2)}` : '—'}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Open Positions */}
      {positions.filter((p) => !p.isClosed).length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">Open Positions</h3>
          <div className="space-y-2">
            {positions
              .filter((p) => !p.isClosed)
              .map((pos) => (
                <motion.div
                  key={pos.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-3 bg-cyan-500/5 border border-cyan-500/30 rounded-sm"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="text-white font-semibold">{pos.market}</div>
                    <span className={pos.direction === 'YES' ? 'text-green-400' : 'text-red-400'}>{pos.direction}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-xs text-gray-400">
                    <div>Entry: ${pos.entryPrice.toFixed(3)}</div>
                    <div>Current: ${pos.currentPrice.toFixed(3)}</div>
                    <div className={pos.unrealizedPnl > 0 ? 'text-green-400' : 'text-red-400'}>
                      {pos.unrealizedPnl > 0 ? '+' : ''}${pos.unrealizedPnl.toFixed(2)}
                    </div>
                  </div>
                </motion.div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};
