import { api } from "@/lib/api";
import type {
  Candle,
  CandlesQuery,
  HistoricalSyncRequest,
  HistoricalSyncResult,
  Instrument,
  InstrumentCreate,
  Quote,
} from "@/types";

export const marketDataService = {
  instruments: (search = "", limit = 50, signal?: AbortSignal) =>
    api.get<Instrument[]>("/market-data/instruments", { search, limit }, signal),
  createInstrument: (body: InstrumentCreate) =>
    api.post<Instrument>("/market-data/instruments", body),
  quotes: (symbols: string[], exchange = "NSE") =>
    api.get<Quote[]>("/market-data/quotes", { symbols: symbols.join(","), exchange }),
  candles: (query: CandlesQuery) => api.get<Candle[]>("/market-data/candles", query),
  syncHistorical: (body: HistoricalSyncRequest) =>
    api.post<HistoricalSyncResult>("/market-data/historical/sync", body),
};
