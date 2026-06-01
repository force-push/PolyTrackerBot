/**
 * Core types for PolyTracker dashboard
 */

export enum ExecutionMode {
  DRY_RUN = 'dry_run',
  DEMO = 'demo',
  LIVE = 'live',
}

export interface Signal {
  id: string;
  timestamp: number;
  whaleAddress: string;
  whaleScore: number;
  market: string;
  marketId: string;
  direction: 'YES' | 'NO';
  whaleSize: number;
  alertType: 'standard' | 'high_conviction';
  signalStrength: number;
  status: 'pending' | 'executed' | 'blocked' | 'failed';
}

export interface Order {
  id: number;
  orderId?: string;
  market: string;
  direction: 'YES' | 'NO';
  sizeUsd: number;
  entryPrice?: number;
  status: 'pending' | 'placed' | 'filled' | 'cancelled' | 'failed';
  executionMode: ExecutionMode;
  createdAt: number;
  filledAt?: number;
  pnl?: number;
  roi?: number;
  errorMessage?: string;
}

export interface Position {
  id: number;
  market: string;
  direction: 'YES' | 'NO';
  sizeUsd: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedRoi: number;
  createdAt: number;
  isClosed: boolean;
}

export interface RiskEvent {
  id: number;
  timestamp: number;
  type: string;
  severity: 'warning' | 'critical';
  description: string;
  actionTaken?: string;
  currentValue?: number;
  limitValue?: number;
}

export interface ExecutionStats {
  ordersPlaced: number;
  ordersFilled: number;
  totalPnl: number;
  winRate: number;
  winningTrades: number;
  losingTrades: number;
  maxConcurrentPositions: number;
  riskEvents: number;
}

export interface WebSocketMessage {
  type: 'signal' | 'order' | 'position' | 'risk_event' | 'stats' | 'config';
  data: any;
  timestamp: number;
}

export interface DashboardConfig {
  executionMode: ExecutionMode;
  defaultPositionSize: number;
  maxPositionSize: number;
  maxDailyLoss: number;
  maxDailyVolume: number;
  maxConcurrentPositions: number;
}
