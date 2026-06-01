/**
 * Zustand store for dashboard state management
 */

import { create } from 'zustand';
import { Signal, Order, Position, RiskEvent, ExecutionStats, DashboardConfig, ExecutionMode } from './types';

interface DashboardState {
  // Data
  signals: Signal[];
  orders: Order[];
  positions: Position[];
  riskEvents: RiskEvent[];
  stats: ExecutionStats;
  config: DashboardConfig;

  // UI State
  isConnected: boolean;
  selectedSignalId: string | null;
  expandedPositions: Set<number>;
  isConfigOpen: boolean;

  // Actions
  addSignal: (signal: Signal) => void;
  addOrder: (order: Order) => void;
  updateOrder: (id: number, updates: Partial<Order>) => void;
  addPosition: (position: Position) => void;
  updatePosition: (id: number, updates: Partial<Position>) => void;
  addRiskEvent: (event: RiskEvent) => void;
  updateStats: (stats: Partial<ExecutionStats>) => void;
  updateConfig: (config: Partial<DashboardConfig>) => void;
  setConnected: (connected: boolean) => void;
  selectSignal: (id: string | null) => void;
  togglePosition: (id: number) => void;
  toggleConfig: () => void;
  clearHistory: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  signals: [],
  orders: [],
  positions: [],
  riskEvents: [],
  stats: {
    ordersPlaced: 0,
    ordersFilled: 0,
    totalPnl: 0,
    winRate: 0,
    winningTrades: 0,
    losingTrades: 0,
    maxConcurrentPositions: 0,
    riskEvents: 0,
  },
  config: {
    executionMode: ExecutionMode.DRY_RUN,
    defaultPositionSize: 500,
    maxPositionSize: 50000,
    maxDailyLoss: 5000,
    maxDailyVolume: 50000,
    maxConcurrentPositions: 10,
  },

  isConnected: false,
  selectedSignalId: null,
  expandedPositions: new Set(),
  isConfigOpen: false,

  addSignal: (signal) =>
    set((state) => ({
      signals: [signal, ...state.signals].slice(0, 100), // Keep last 100
    })),

  addOrder: (order) =>
    set((state) => ({
      orders: [order, ...state.orders].slice(0, 100),
    })),

  updateOrder: (id, updates) =>
    set((state) => ({
      orders: state.orders.map((o) => (o.id === id ? { ...o, ...updates } : o)),
    })),

  addPosition: (position) =>
    set((state) => ({
      positions: [position, ...state.positions],
    })),

  updatePosition: (id, updates) =>
    set((state) => ({
      positions: state.positions.map((p) => (p.id === id ? { ...p, ...updates } : p)),
    })),

  addRiskEvent: (event) =>
    set((state) => ({
      riskEvents: [event, ...state.riskEvents].slice(0, 50),
    })),

  updateStats: (stats) =>
    set((state) => ({
      stats: { ...state.stats, ...stats },
    })),

  updateConfig: (config) =>
    set((state) => ({
      config: { ...state.config, ...config },
    })),

  setConnected: (connected) =>
    set(() => ({
      isConnected: connected,
    })),

  selectSignal: (id) =>
    set(() => ({
      selectedSignalId: id,
    })),

  togglePosition: (id) =>
    set((state) => ({
      expandedPositions: new Set(
        state.expandedPositions.has(id)
          ? Array.from(state.expandedPositions).filter((p) => p !== id)
          : [...Array.from(state.expandedPositions), id]
      ),
    })),

  toggleConfig: () =>
    set((state) => ({
      isConfigOpen: !state.isConfigOpen,
    })),

  clearHistory: () =>
    set(() => ({
      signals: [],
      orders: [],
      positions: [],
      riskEvents: [],
    })),
}));
