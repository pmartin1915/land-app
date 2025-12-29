/**
 * TopBar Component Tests
 *
 * Tests for the main navigation/search bar component.
 * Demonstrates Vitest + React Testing Library patterns.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../test/test-utils'
import { TopBar } from './TopBar'

// Mock the hooks
vi.mock('../lib/hooks', () => ({
  usePropertySearch: vi.fn(() => ({
    data: [],
    isSearching: false,
  })),
  useCounties: vi.fn(() => ({
    data: [
      { code: 'MOBILE', name: 'Mobile' },
      { code: 'BALDWIN', name: 'Baldwin' },
    ],
  })),
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

describe('TopBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders the title', () => {
      render(<TopBar title="Dashboard" />)

      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument()
    })

    it('renders the search input', () => {
      render(<TopBar title="Dashboard" />)

      expect(screen.getByPlaceholderText(/search properties/i)).toBeInTheDocument()
    })

    it('renders the Filters button', () => {
      render(<TopBar title="Dashboard" />)

      expect(screen.getByRole('button', { name: /filters/i })).toBeInTheDocument()
    })

    it('renders the Actions dropdown button', () => {
      render(<TopBar title="Dashboard" />)

      expect(screen.getByRole('button', { name: /actions/i })).toBeInTheDocument()
    })

    it('renders the period selector', () => {
      render(<TopBar title="Dashboard" />)

      expect(screen.getByRole('combobox')).toBeInTheDocument()
      expect(screen.getByText(/last 7 days/i)).toBeInTheDocument()
    })
  })

  describe('Search Functionality', () => {
    it('updates search input value on type', async () => {
      render(<TopBar title="Dashboard" />)

      const searchInput = screen.getByPlaceholderText(/search properties/i)
      fireEvent.change(searchInput, { target: { value: 'Mobile County' } })

      expect(searchInput).toHaveValue('Mobile County')
    })

    it('calls onSearchChange when search input changes', async () => {
      const onSearchChange = vi.fn()
      render(<TopBar title="Dashboard" onSearchChange={onSearchChange} />)

      const searchInput = screen.getByPlaceholderText(/search properties/i)
      fireEvent.change(searchInput, { target: { value: 'test' } })

      expect(onSearchChange).toHaveBeenCalledWith('test', [])
    })
  })

  describe('Filter Popover', () => {
    it('opens filter popover when Filters button is clicked', async () => {
      render(<TopBar title="Dashboard" />)

      const filtersButton = screen.getByRole('button', { name: /filters/i })
      fireEvent.click(filtersButton)

      await waitFor(() => {
        expect(screen.getByText(/advanced filters/i)).toBeInTheDocument()
      })
    })

    it('shows county dropdown in filter popover', async () => {
      render(<TopBar title="Dashboard" />)

      const filtersButton = screen.getByRole('button', { name: /filters/i })
      fireEvent.click(filtersButton)

      await waitFor(() => {
        expect(screen.getByText(/all counties/i)).toBeInTheDocument()
      })
    })

    it('closes filter popover when clicking Apply Filters', async () => {
      render(<TopBar title="Dashboard" />)

      // Open the popover
      const filtersButton = screen.getByRole('button', { name: /filters/i })
      fireEvent.click(filtersButton)

      // Click Apply Filters
      const applyButton = await screen.findByRole('button', { name: /apply filters/i })
      fireEvent.click(applyButton)

      await waitFor(() => {
        expect(screen.queryByText(/advanced filters/i)).not.toBeInTheDocument()
      })
    })

    it('calls onFiltersChange when filters are applied', async () => {
      const onFiltersChange = vi.fn()
      render(<TopBar title="Dashboard" onFiltersChange={onFiltersChange} />)

      // Open the popover
      const filtersButton = screen.getByRole('button', { name: /filters/i })
      fireEvent.click(filtersButton)

      // Click Apply Filters
      const applyButton = await screen.findByRole('button', { name: /apply filters/i })
      fireEvent.click(applyButton)

      expect(onFiltersChange).toHaveBeenCalled()
    })

    it('resets filters when Reset button is clicked', async () => {
      const onFiltersChange = vi.fn()
      render(<TopBar title="Dashboard" onFiltersChange={onFiltersChange} />)

      // Open the popover
      fireEvent.click(screen.getByRole('button', { name: /filters/i }))

      // Click Reset
      const resetButton = await screen.findByRole('button', { name: /reset/i })
      fireEvent.click(resetButton)

      expect(onFiltersChange).toHaveBeenCalledWith({})
    })
  })

  describe('Actions Dropdown', () => {
    it('opens actions dropdown when clicked', async () => {
      render(<TopBar title="Dashboard" />)

      const actionsButton = screen.getByRole('button', { name: /actions/i })
      fireEvent.click(actionsButton)

      await waitFor(() => {
        expect(screen.getByText(/export data/i)).toBeInTheDocument()
        expect(screen.getByText(/import csv/i)).toBeInTheDocument()
        expect(screen.getByText(/new scrape/i)).toBeInTheDocument()
        expect(screen.getByText(/settings/i)).toBeInTheDocument()
      })
    })
  })

  describe('Period Selector', () => {
    it('has correct default value', () => {
      render(<TopBar title="Dashboard" />)

      const select = screen.getByRole('combobox')
      expect(select).toHaveValue('last-7-days')
    })

    it('has all period options', () => {
      render(<TopBar title="Dashboard" />)

      expect(screen.getByText(/last 24 hours/i)).toBeInTheDocument()
      expect(screen.getByText(/last 7 days/i)).toBeInTheDocument()
      expect(screen.getByText(/last 30 days/i)).toBeInTheDocument()
      expect(screen.getByText(/last quarter/i)).toBeInTheDocument()
      expect(screen.getByText(/last year/i)).toBeInTheDocument()
      expect(screen.getByText(/all time/i)).toBeInTheDocument()
    })
  })
})
