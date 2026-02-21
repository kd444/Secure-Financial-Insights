import { create } from "zustand"
import type { RecentQuery, IngestionRecord } from "./types"

interface AppState {
  recentQueries: RecentQuery[]
  addQuery: (query: RecentQuery) => void
  ingestionHistory: IngestionRecord[]
  addIngestion: (record: IngestionRecord) => void
  queriesToday: number
  incrementQueriesToday: () => void
  avgConfidence: number
  avgHallucination: number
  updateAverages: (confidence: number, hallucination: number) => void
  sidebarCollapsed: boolean
  toggleSidebar: () => void
}

export const useAppStore = create<AppState>((set) => ({
  recentQueries: [],
  addQuery: (query) =>
    set((state) => ({
      recentQueries: [query, ...state.recentQueries].slice(0, 50),
    })),
  ingestionHistory: [],
  addIngestion: (record) =>
    set((state) => ({
      ingestionHistory: [record, ...state.ingestionHistory].slice(0, 50),
    })),
  queriesToday: 0,
  incrementQueriesToday: () =>
    set((state) => ({ queriesToday: state.queriesToday + 1 })),
  avgConfidence: 0,
  avgHallucination: 0,
  updateAverages: (confidence, hallucination) =>
    set((state) => {
      const total = state.queriesToday || 1
      const newAvgConfidence =
        (state.avgConfidence * (total - 1) + confidence) / total
      const newAvgHallucination =
        (state.avgHallucination * (total - 1) + hallucination) / total
      return {
        avgConfidence: newAvgConfidence,
        avgHallucination: newAvgHallucination,
      }
    }),
  sidebarCollapsed: false,
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
}))
