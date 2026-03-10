/**
 * Context and Reducer Tests
 *
 * Tests for the AppContext and useApp hook.
 * Tests the reducer logic and context behavior.
 */

import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import React from 'react'
import { AppProvider, useApp } from './context'

describe('useApp Hook', () => {
  describe('Error Handling', () => {
    it('throws error when used outside AppProvider', () => {
      // Suppress console.error for this test since we expect an error
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      expect(() => {
        renderHook(() => useApp())
      }).toThrow('useApp must be used within an AppProvider')

      consoleSpy.mockRestore()
    })
  })

  describe('Hook Behavior', () => {
    it('returns state and dispatch when used inside AppProvider', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current).toBeDefined()
      expect(result.current.state).toBeDefined()
      expect(result.current.dispatch).toBeDefined()
    })

    it('returns initial state with correct default values', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current.state).toEqual({
        user: null,
        theme: 'dark',
        selectedProperties: [],
        filters: {},
        loading: false,
        error: null,
      })
    })
  })

  describe('Reducer: SET_THEME', () => {
    it('changes theme to light', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current.state.theme).toBe('dark')

      act(() => {
        result.current.dispatch({ type: 'SET_THEME', payload: 'light' })
      })

      expect(result.current.state.theme).toBe('light')
    })

    it('changes theme to dark', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      // First set to light
      act(() => {
        result.current.dispatch({ type: 'SET_THEME', payload: 'light' })
      })

      expect(result.current.state.theme).toBe('light')

      // Then set to dark
      act(() => {
        result.current.dispatch({ type: 'SET_THEME', payload: 'dark' })
      })

      expect(result.current.state.theme).toBe('dark')
    })
  })

  describe('Reducer: SET_LOADING', () => {
    it('sets loading to true', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current.state.loading).toBe(false)

      act(() => {
        result.current.dispatch({ type: 'SET_LOADING', payload: true })
      })

      expect(result.current.state.loading).toBe(true)
    })

    it('sets loading to false', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      // First set to true
      act(() => {
        result.current.dispatch({ type: 'SET_LOADING', payload: true })
      })

      expect(result.current.state.loading).toBe(true)

      // Then set to false
      act(() => {
        result.current.dispatch({ type: 'SET_LOADING', payload: false })
      })

      expect(result.current.state.loading).toBe(false)
    })

    it('toggles loading flag multiple times', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      act(() => {
        result.current.dispatch({ type: 'SET_LOADING', payload: true })
      })
      expect(result.current.state.loading).toBe(true)

      act(() => {
        result.current.dispatch({ type: 'SET_LOADING', payload: false })
      })
      expect(result.current.state.loading).toBe(false)

      act(() => {
        result.current.dispatch({ type: 'SET_LOADING', payload: true })
      })
      expect(result.current.state.loading).toBe(true)
    })
  })

  describe('Reducer: SET_ERROR', () => {
    it('sets error message', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current.state.error).toBe(null)

      act(() => {
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: 'Something went wrong',
        })
      })

      expect(result.current.state.error).toBe('Something went wrong')
    })

    it('updates error message', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      act(() => {
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: 'First error',
        })
      })

      expect(result.current.state.error).toBe('First error')

      act(() => {
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: 'Second error',
        })
      })

      expect(result.current.state.error).toBe('Second error')
    })

    it('sets error to null', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      // First set an error
      act(() => {
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: 'An error occurred',
        })
      })

      expect(result.current.state.error).toBe('An error occurred')

      // Then clear it
      act(() => {
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: null,
        })
      })

      expect(result.current.state.error).toBe(null)
    })
  })

  describe('Reducer: CLEAR_ERROR', () => {
    it('resets error to null', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      // Set an error first
      act(() => {
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: 'An error message',
        })
      })

      expect(result.current.state.error).toBe('An error message')

      // Clear the error
      act(() => {
        result.current.dispatch({ type: 'CLEAR_ERROR' })
      })

      expect(result.current.state.error).toBe(null)
    })

    it('handles CLEAR_ERROR when no error exists', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current.state.error).toBe(null)

      act(() => {
        result.current.dispatch({ type: 'CLEAR_ERROR' })
      })

      expect(result.current.state.error).toBe(null)
    })
  })

  describe('Reducer: SET_SELECTED_PROPERTIES', () => {
    it('sets selectedProperties array', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current.state.selectedProperties).toEqual([])

      const properties = ['prop1', 'prop2', 'prop3']

      act(() => {
        result.current.dispatch({
          type: 'SET_SELECTED_PROPERTIES',
          payload: properties,
        })
      })

      expect(result.current.state.selectedProperties).toEqual(properties)
    })

    it('replaces selectedProperties array with new array', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      const firstProperties = ['prop1', 'prop2']

      act(() => {
        result.current.dispatch({
          type: 'SET_SELECTED_PROPERTIES',
          payload: firstProperties,
        })
      })

      expect(result.current.state.selectedProperties).toEqual(firstProperties)

      const secondProperties = ['prop3', 'prop4', 'prop5']

      act(() => {
        result.current.dispatch({
          type: 'SET_SELECTED_PROPERTIES',
          payload: secondProperties,
        })
      })

      expect(result.current.state.selectedProperties).toEqual(secondProperties)
    })

    it('clears selectedProperties with empty array', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      // Set properties
      act(() => {
        result.current.dispatch({
          type: 'SET_SELECTED_PROPERTIES',
          payload: ['prop1', 'prop2'],
        })
      })

      expect(result.current.state.selectedProperties).toEqual(['prop1', 'prop2'])

      // Clear properties
      act(() => {
        result.current.dispatch({
          type: 'SET_SELECTED_PROPERTIES',
          payload: [],
        })
      })

      expect(result.current.state.selectedProperties).toEqual([])
    })

    it('handles single property in array', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      act(() => {
        result.current.dispatch({
          type: 'SET_SELECTED_PROPERTIES',
          payload: ['single_prop'],
        })
      })

      expect(result.current.state.selectedProperties).toEqual(['single_prop'])
    })
  })

  describe('Reducer: SET_FILTERS', () => {
    it('sets filters object', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      expect(result.current.state.filters).toEqual({})

      const filters = { county: 'Mobile', priceMin: 100000 }

      act(() => {
        result.current.dispatch({
          type: 'SET_FILTERS',
          payload: filters,
        })
      })

      expect(result.current.state.filters).toEqual(filters)
    })

    it('replaces filters object with new object', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      const firstFilters = { county: 'Mobile' }

      act(() => {
        result.current.dispatch({
          type: 'SET_FILTERS',
          payload: firstFilters,
        })
      })

      expect(result.current.state.filters).toEqual(firstFilters)

      const secondFilters = { county: 'Baldwin', priceMin: 50000, priceMax: 200000 }

      act(() => {
        result.current.dispatch({
          type: 'SET_FILTERS',
          payload: secondFilters,
        })
      })

      expect(result.current.state.filters).toEqual(secondFilters)
    })

    it('clears filters with empty object', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      // Set filters
      act(() => {
        result.current.dispatch({
          type: 'SET_FILTERS',
          payload: { county: 'Mobile', priceMin: 100000 },
        })
      })

      expect(result.current.state.filters).not.toEqual({})

      // Clear filters
      act(() => {
        result.current.dispatch({
          type: 'SET_FILTERS',
          payload: {},
        })
      })

      expect(result.current.state.filters).toEqual({})
    })

    it('handles complex filter objects', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      const complexFilters = {
        county: 'Mobile',
        priceMin: 50000,
        priceMax: 500000,
        sortBy: 'date',
        limit: 50,
        tags: ['auction', 'featured'],
      }

      act(() => {
        result.current.dispatch({
          type: 'SET_FILTERS',
          payload: complexFilters,
        })
      })

      expect(result.current.state.filters).toEqual(complexFilters)
    })
  })

  describe('Unknown Action Type', () => {
    it('returns unchanged state for unknown action', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      const initialState = { ...result.current.state }

      act(() => {
        result.current.dispatch({
          type: 'UNKNOWN_ACTION' as any,
        })
      })

      expect(result.current.state).toEqual(initialState)
    })
  })

  describe('Multiple Dispatch Actions', () => {
    it('dispatches multiple actions sequentially', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      act(() => {
        result.current.dispatch({ type: 'SET_THEME', payload: 'light' })
        result.current.dispatch({ type: 'SET_LOADING', payload: true })
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: 'Test error',
        })
      })

      expect(result.current.state.theme).toBe('light')
      expect(result.current.state.loading).toBe(true)
      expect(result.current.state.error).toBe('Test error')
    })

    it('dispatches actions that modify different parts of state', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      act(() => {
        result.current.dispatch({
          type: 'SET_SELECTED_PROPERTIES',
          payload: ['prop1', 'prop2'],
        })
        result.current.dispatch({
          type: 'SET_FILTERS',
          payload: { county: 'Mobile' },
        })
        result.current.dispatch({ type: 'SET_LOADING', payload: true })
      })

      expect(result.current.state.selectedProperties).toEqual(['prop1', 'prop2'])
      expect(result.current.state.filters).toEqual({ county: 'Mobile' })
      expect(result.current.state.loading).toBe(true)
    })

    it('can set and clear error in sequence', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      act(() => {
        result.current.dispatch({
          type: 'SET_ERROR',
          payload: 'Error message',
        })
      })

      expect(result.current.state.error).toBe('Error message')

      act(() => {
        result.current.dispatch({ type: 'CLEAR_ERROR' })
      })

      expect(result.current.state.error).toBe(null)
    })
  })

  describe('State Immutability', () => {
    it('does not mutate existing state when dispatching actions', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      const stateBefore = result.current.state

      act(() => {
        result.current.dispatch({ type: 'SET_THEME', payload: 'light' })
      })

      // Original state reference should not change (new state object is created)
      expect(stateBefore !== result.current.state).toBe(true)
      expect(stateBefore.theme).toBe('dark')
      expect(result.current.state.theme).toBe('light')
    })

    it('preserves unmodified state properties when updating other properties', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AppProvider>{children}</AppProvider>
      )

      const { result } = renderHook(() => useApp(), { wrapper })

      const initialUser = result.current.state.user
      const initialSelectedProperties = result.current.state.selectedProperties
      const initialFilters = result.current.state.filters

      act(() => {
        result.current.dispatch({ type: 'SET_THEME', payload: 'light' })
      })

      expect(result.current.state.user).toBe(initialUser)
      expect(result.current.state.selectedProperties).toBe(initialSelectedProperties)
      expect(result.current.state.filters).toBe(initialFilters)
    })
  })
})

