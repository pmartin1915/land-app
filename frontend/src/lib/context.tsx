import React, { createContext, useContext, useReducer, ReactNode } from 'react'

// App State Interface
interface AppState {
  user: unknown | null
  theme: 'light' | 'dark'
  selectedProperties: string[]
  filters: Record<string, unknown>
  loading: boolean
  error: string | null
}

// Initial State
const initialState: AppState = {
  user: null,
  theme: 'dark',
  selectedProperties: [],
  filters: {},
  loading: false,
  error: null,
}

// Action Types
type AppAction =
  | { type: 'SET_THEME'; payload: 'light' | 'dark' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_SELECTED_PROPERTIES'; payload: string[] }
  | { type: 'SET_FILTERS'; payload: Record<string, unknown> }
  | { type: 'CLEAR_ERROR' }

// Reducer
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_THEME':
      return { ...state, theme: action.payload }
    case 'SET_LOADING':
      return { ...state, loading: action.payload }
    case 'SET_ERROR':
      return { ...state, error: action.payload }
    case 'SET_SELECTED_PROPERTIES':
      return { ...state, selectedProperties: action.payload }
    case 'SET_FILTERS':
      return { ...state, filters: action.payload }
    case 'CLEAR_ERROR':
      return { ...state, error: null }
    default:
      return state
  }
}

// Context
const AppContext = createContext<{
  state: AppState
  dispatch: React.Dispatch<AppAction>
} | null>(null)

// Provider
export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState)

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  )
}

// Hook
// eslint-disable-next-line react-refresh/only-export-components
export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}