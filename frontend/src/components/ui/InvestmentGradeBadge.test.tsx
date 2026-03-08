import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/test-utils'
import {
  InvestmentGradeBadge,
  getGradeLetter,
  getGradeDetails,
} from './InvestmentGradeBadge'

// Mock ScoreTooltip
vi.mock('./ScoreTooltip', () => ({
  ScoreTooltip: () => <span data-testid="score-tooltip" />,
}))

describe('getGradeLetter', () => {
  describe('grade boundaries', () => {
    it('should return "A" for score >= 80', () => {
      expect(getGradeLetter(80)).toBe('A')
      expect(getGradeLetter(85)).toBe('A')
      expect(getGradeLetter(100)).toBe('A')
    })

    it('should return "B" for score 60-79', () => {
      expect(getGradeLetter(60)).toBe('B')
      expect(getGradeLetter(70)).toBe('B')
      expect(getGradeLetter(79)).toBe('B')
    })

    it('should return "C" for score 40-59', () => {
      expect(getGradeLetter(40)).toBe('C')
      expect(getGradeLetter(50)).toBe('C')
      expect(getGradeLetter(59)).toBe('C')
    })

    it('should return "D" for score < 40', () => {
      expect(getGradeLetter(0)).toBe('D')
      expect(getGradeLetter(20)).toBe('D')
      expect(getGradeLetter(39)).toBe('D')
    })

    it('should return "-" for null score', () => {
      expect(getGradeLetter(null)).toBe('-')
    })

    it('should return "-" for undefined score', () => {
      expect(getGradeLetter(undefined)).toBe('-')
    })
  })

  describe('boundary values', () => {
    it('should correctly handle boundary at 80 (A/B)', () => {
      expect(getGradeLetter(79)).toBe('B')
      expect(getGradeLetter(80)).toBe('A')
    })

    it('should correctly handle boundary at 60 (B/C)', () => {
      expect(getGradeLetter(59)).toBe('C')
      expect(getGradeLetter(60)).toBe('B')
    })

    it('should correctly handle boundary at 40 (C/D)', () => {
      expect(getGradeLetter(39)).toBe('D')
      expect(getGradeLetter(40)).toBe('C')
    })
  })
})

describe('getGradeDetails', () => {
  it('should return grade "A" with label "Excellent" for score >= 80', () => {
    const details = getGradeDetails(80)
    expect(details.grade).toBe('A')
    expect(details.label).toBe('Excellent')
    expect(details.color).toBe('text-success')
    expect(details.bgColor).toBe('bg-success/10')
  })

  it('should return grade "B" with label "Good" for score 60-79', () => {
    const details = getGradeDetails(70)
    expect(details.grade).toBe('B')
    expect(details.label).toBe('Good')
    expect(details.color).toBe('text-accent-primary')
    expect(details.bgColor).toBe('bg-accent-primary/10')
  })

  it('should return grade "C" with label "Fair" for score 40-59', () => {
    const details = getGradeDetails(50)
    expect(details.grade).toBe('C')
    expect(details.label).toBe('Fair')
    expect(details.color).toBe('text-warning')
    expect(details.bgColor).toBe('bg-warning/10')
  })

  it('should return grade "D" with label "Poor" for score < 40', () => {
    const details = getGradeDetails(30)
    expect(details.grade).toBe('D')
    expect(details.label).toBe('Poor')
    expect(details.color).toBe('text-danger')
    expect(details.bgColor).toBe('bg-danger/10')
  })

  it('should return grade "-" with label "No Score" for null score', () => {
    const details = getGradeDetails(null)
    expect(details.grade).toBe('-')
    expect(details.label).toBe('No Score')
    expect(details.color).toBe('text-text-muted')
    expect(details.bgColor).toBe('bg-neutral-1')
  })

  it('should return grade "-" with label "No Score" for undefined score', () => {
    const details = getGradeDetails(undefined)
    expect(details.grade).toBe('-')
    expect(details.label).toBe('No Score')
    expect(details.color).toBe('text-text-muted')
    expect(details.bgColor).toBe('bg-neutral-1')
  })
})

describe('InvestmentGradeBadge component', () => {
  describe('rendering grade letter', () => {
    it('should render "A" for score >= 80', () => {
      render(<InvestmentGradeBadge score={80} />)
      expect(screen.getByText('A')).toBeInTheDocument()
    })

    it('should render "B" for score 60-79', () => {
      render(<InvestmentGradeBadge score={70} />)
      expect(screen.getByText('B')).toBeInTheDocument()
    })

    it('should render "C" for score 40-59', () => {
      render(<InvestmentGradeBadge score={50} />)
      expect(screen.getByText('C')).toBeInTheDocument()
    })

    it('should render "D" for score < 40', () => {
      render(<InvestmentGradeBadge score={20} />)
      expect(screen.getByText('D')).toBeInTheDocument()
    })
  })

  describe('rendering with null/undefined score', () => {
    it('should render "-" for null score', () => {
      render(<InvestmentGradeBadge score={null} />)
      expect(screen.getByText('-')).toBeInTheDocument()
    })

    it('should render "-" for undefined score', () => {
      render(<InvestmentGradeBadge score={undefined} />)
      expect(screen.getByText('-')).toBeInTheDocument()
    })
  })

  describe('aria-label', () => {
    it('should have correct aria-label for grade A', () => {
      render(<InvestmentGradeBadge score={80} />)
      const badge = screen.getByText('A')
      expect(badge).toHaveAttribute('aria-label', 'Investment Grade: A (Excellent)')
    })

    it('should have correct aria-label for grade B', () => {
      render(<InvestmentGradeBadge score={70} />)
      const badge = screen.getByText('B')
      expect(badge).toHaveAttribute('aria-label', 'Investment Grade: B (Good)')
    })

    it('should have correct aria-label for grade C', () => {
      render(<InvestmentGradeBadge score={50} />)
      const badge = screen.getByText('C')
      expect(badge).toHaveAttribute('aria-label', 'Investment Grade: C (Fair)')
    })

    it('should have correct aria-label for grade D', () => {
      render(<InvestmentGradeBadge score={30} />)
      const badge = screen.getByText('D')
      expect(badge).toHaveAttribute('aria-label', 'Investment Grade: D (Poor)')
    })

    it('should have correct aria-label for no score', () => {
      render(<InvestmentGradeBadge score={null} />)
      const badge = screen.getByText('-')
      expect(badge).toHaveAttribute('aria-label', 'Investment Grade: - (No Score)')
    })
  })

  describe('title attribute', () => {
    it('should have title attribute when showTooltip is false', () => {
      render(<InvestmentGradeBadge score={80} showTooltip={false} />)
      const badge = screen.getByText('A')
      expect(badge).toHaveAttribute('title', 'A - Excellent')
    })

    it('should not have title attribute when showTooltip is true', () => {
      render(<InvestmentGradeBadge score={80} showTooltip={true} />)
      const badge = screen.getByText('A')
      expect(badge).not.toHaveAttribute('title')
    })
  })

  describe('size classes', () => {
    it('should apply sm size classes', () => {
      const { container } = render(<InvestmentGradeBadge score={80} size="sm" />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('w-5', 'h-5', 'text-xs')
    })

    it('should apply md size classes', () => {
      const { container } = render(<InvestmentGradeBadge score={80} size="md" />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('w-7', 'h-7', 'text-sm')
    })

    it('should apply lg size classes', () => {
      const { container } = render(<InvestmentGradeBadge score={80} size="lg" />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('w-9', 'h-9', 'text-base')
    })

    it('should default to md size', () => {
      const { container } = render(<InvestmentGradeBadge score={80} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('w-7', 'h-7', 'text-sm')
    })
  })

  describe('color classes', () => {
    it('should apply success color classes for grade A', () => {
      const { container } = render(<InvestmentGradeBadge score={80} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('text-success', 'bg-success/10')
    })

    it('should apply accent-primary color classes for grade B', () => {
      const { container } = render(<InvestmentGradeBadge score={70} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('text-accent-primary', 'bg-accent-primary/10')
    })

    it('should apply warning color classes for grade C', () => {
      const { container } = render(<InvestmentGradeBadge score={50} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('text-warning', 'bg-warning/10')
    })

    it('should apply danger color classes for grade D', () => {
      const { container } = render(<InvestmentGradeBadge score={30} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('text-danger', 'bg-danger/10')
    })

    it('should apply muted color classes for no score', () => {
      const { container } = render(<InvestmentGradeBadge score={null} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('text-text-muted', 'bg-neutral-1')
    })
  })

  describe('tooltip functionality', () => {
    it('should not show tooltip when showTooltip is false', () => {
      render(<InvestmentGradeBadge score={80} showTooltip={false} />)
      expect(screen.queryByTestId('score-tooltip')).not.toBeInTheDocument()
    })

    it('should show tooltip when showTooltip is true', () => {
      render(<InvestmentGradeBadge score={80} showTooltip={true} />)
      expect(screen.getByTestId('score-tooltip')).toBeInTheDocument()
    })

    it('should wrap badge and tooltip in inline-flex container when showTooltip is true', () => {
      const { container } = render(<InvestmentGradeBadge score={80} showTooltip={true} />)
      const wrapper = container.querySelector('.inline-flex.items-center.gap-1')
      expect(wrapper).toBeInTheDocument()
      expect(wrapper).toContainElement(screen.getByText('A'))
      expect(wrapper).toContainElement(screen.getByTestId('score-tooltip'))
    })

    it('should render badge without wrapper when showTooltip is false', () => {
      const { container } = render(<InvestmentGradeBadge score={80} showTooltip={false} />)
      const wrappers = container.querySelectorAll('.inline-flex.items-center.gap-1')
      expect(wrappers.length).toBe(0)
    })
  })

  describe('custom className', () => {
    it('should apply custom className to badge', () => {
      const { container } = render(
        <InvestmentGradeBadge score={80} className="custom-class" />
      )
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('custom-class')
    })

    it('should preserve other classes with custom className', () => {
      const { container } = render(
        <InvestmentGradeBadge score={80} className="custom-class" />
      )
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass(
        'inline-flex',
        'items-center',
        'justify-center',
        'rounded-md',
        'font-bold',
        'custom-class'
      )
    })
  })

  describe('badge element structure', () => {
    it('should render as a div with inline-flex display', () => {
      render(<InvestmentGradeBadge score={80} />)
      const badge = screen.getByText('A')
      expect(badge.tagName).toBe('DIV')
      expect(badge).toHaveClass('inline-flex')
    })

    it('should have rounded-md class for rounded corners', () => {
      const { container } = render(<InvestmentGradeBadge score={80} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('rounded-md')
    })

    it('should have font-bold class for text styling', () => {
      const { container } = render(<InvestmentGradeBadge score={80} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('font-bold')
    })

    it('should center content with items-center and justify-center', () => {
      const { container } = render(<InvestmentGradeBadge score={80} />)
      const badge = container.querySelector('div[aria-label]')
      expect(badge).toHaveClass('items-center', 'justify-center')
    })
  })

  describe('edge cases', () => {
    it('should handle score of 0', () => {
      render(<InvestmentGradeBadge score={0} />)
      expect(screen.getByText('D')).toBeInTheDocument()
    })

    it('should handle very high score', () => {
      render(<InvestmentGradeBadge score={999} />)
      expect(screen.getByText('A')).toBeInTheDocument()
    })

    it('should handle negative score', () => {
      render(<InvestmentGradeBadge score={-10} />)
      expect(screen.getByText('D')).toBeInTheDocument()
    })

    it('should handle decimal scores', () => {
      render(<InvestmentGradeBadge score={80.5} />)
      expect(screen.getByText('A')).toBeInTheDocument()
    })

    it('should handle score just below boundary', () => {
      render(<InvestmentGradeBadge score={79.9} />)
      expect(screen.getByText('B')).toBeInTheDocument()
    })
  })
})
