import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'

type Theme = 'light' | 'dark' | 'system'

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  isDark: boolean
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

interface ThemeProviderProps {
  children: ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

export function ThemeProvider({
  children,
  defaultTheme = 'dark',
  storageKey = 'aaw-theme',
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => {
    // Try to get theme from localStorage first
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey)
      if (stored && ['light', 'dark', 'system'].includes(stored)) {
        return stored as Theme
      }
    }
    return defaultTheme
  })

  const [isDark, setIsDark] = useState(() => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return theme === 'dark'
  })

  useEffect(() => {
    const root = document.documentElement

    // Remove previous theme classes
    root.classList.remove('light', 'dark')

    let effectiveTheme: 'light' | 'dark'
    if (theme === 'system') {
      effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    } else {
      effectiveTheme = theme
    }

    // Apply theme class - CSS variables are defined in index.css
    root.classList.add(effectiveTheme)
    setIsDark(effectiveTheme === 'dark')

    // Store theme preference
    localStorage.setItem(storageKey, theme)
  }, [theme, storageKey])

  useEffect(() => {
    // Listen for system theme changes when using 'system' theme
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

      const handleChange = (e: MediaQueryListEvent) => {
        setIsDark(e.matches)
      }

      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [theme])

  // Handle Electron menu theme toggle
  useEffect(() => {
    const handleThemeToggle = () => {
      setTheme(current => current === 'dark' ? 'light' : 'dark')
    }

    // Listen for theme toggle from Electron main process
    if (window.electronAPI) {
      window.electronAPI.onMenuToggleTheme(handleThemeToggle)
    }

    return () => {
      // Cleanup listener if needed
    }
  }, [])

  const value = {
    theme,
    setTheme,
    isDark,
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  const context = useContext(ThemeContext)

  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }

  return context
}

// Theme toggle component
export function ThemeToggle() {
  const { setTheme, isDark } = useTheme()

  const toggleTheme = () => {
    setTheme(isDark ? 'light' : 'dark')
  }

  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg bg-surface hover:bg-card transition-colors duration-150"
      aria-label="Toggle theme"
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      {isDark ? (
        // Sun icon for light mode
        <svg className="w-5 h-5 text-text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ) : (
        // Moon icon for dark mode
        <svg className="w-5 h-5 text-text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  )
}

// Utility hook for component-specific theme values
// eslint-disable-next-line react-refresh/only-export-components
export function useComponentTheme() {
  const { isDark } = useTheme()

  return {
    isDark,
    // Helper functions for common patterns
    getBackground: (level: 'base' | 'surface' | 'card' = 'base') => {
      const backgrounds = {
        base: 'bg-bg',
        surface: 'bg-surface',
        card: 'bg-card',
      }
      return backgrounds[level]
    },
    getText: (level: 'primary' | 'muted' = 'primary') => {
      return level === 'primary' ? 'text-text-primary' : 'text-text-muted'
    },
    getBorder: () => 'border-neutral-1',
    getAccent: (variant: 'primary' | 'alt' = 'primary') => {
      return variant === 'primary' ? 'text-accent-primary' : 'text-accent-alt'
    },
    getSemantic: (type: 'success' | 'warning' | 'danger') => {
      const colors = {
        success: 'text-success',
        warning: 'text-warning',
        danger: 'text-danger',
      }
      return colors[type]
    },
  }
}