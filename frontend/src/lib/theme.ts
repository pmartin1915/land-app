// Design tokens implementation based on specification
export const theme = {
  // Color tokens (dark-first)
  colors: {
    // Background colors
    bg: '#0B0F13',
    surface: '#0F1418',
    card: '#13171B',

    // Text colors
    textPrimary: '#E6EEF3',
    textMuted: '#A8B3BD',

    // Accent colors
    accentPrimary: '#6C8EF5',  // indigo
    accentAlt: '#08A6A6',      // teal (used sparingly)

    // Semantic colors
    success: '#16A34A',
    warning: '#F59E0B',
    danger: '#EF4444',

    // Neutral
    neutral1: '#0C1114',

    // Light mode variants (for future use)
    light: {
      bg: '#FFFFFF',
      surface: '#F8FAFC',
      card: '#FFFFFF',
      textPrimary: '#1F2937',
      textMuted: '#6B7280',
    }
  },

  // Typography tokens
  typography: {
    fontFamily: {
      base: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
    },
    fontSize: {
      caption: '12px',
      body: '14px',
      bodyLarge: '16px',
      headline6: '20px',
      headline5: '24px',
      headline4: '28px',
    },
    lineHeight: {
      caption: '16px',
      body: '20px',
      bodyLarge: '24px',
      headline6: '28px',
      headline5: '32px',
      headline4: '36px',
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    }
  },

  // Spacing tokens (4px base scale)
  spacing: {
    1: '4px',
    2: '8px',
    3: '12px',
    4: '16px',
    5: '20px',
    6: '24px',
    8: '32px',
    10: '40px',
    12: '48px',
    16: '64px',
    20: '80px',
    24: '96px',
  },

  // Border radius tokens
  borderRadius: {
    sm: '4px',
    base: '8px',
    lg: '12px',
    xl: '16px',
  },

  // Shadow tokens (optimized for dark mode)
  shadows: {
    card: '0 6px 18px rgba(2, 6, 23, 0.4)',
    elevated: '0 10px 25px rgba(2, 6, 23, 0.5)',
    focus: '0 0 0 2px #6C8EF5',
  },

  // Animation tokens
  animation: {
    duration: {
      fast: '150ms',
      base: '200ms',
      slow: '300ms',
    },
    easing: {
      easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    }
  },

  // Layout tokens
  layout: {
    leftRailWidth: '256px',
    leftRailWidthCollapsed: '64px',
    topBarHeight: '64px',
    maxContentWidth: '1400px',
  },

  // Z-index tokens
  zIndex: {
    modal: 1000,
    overlay: 900,
    dropdown: 800,
    header: 700,
    sidebar: 600,
  }
} as const

// Theme utilities
export type Theme = typeof theme

// CSS custom properties for runtime theme switching
export const createCSSVariables = (isDark = true) => {
  const colors = isDark ? theme.colors : {
    ...theme.colors,
    ...theme.colors.light,
  }

  return {
    '--color-bg': colors.bg,
    '--color-surface': colors.surface,
    '--color-card': colors.card,
    '--color-text-primary': colors.textPrimary,
    '--color-text-muted': colors.textMuted,
    '--color-accent-primary': colors.accentPrimary,
    '--color-accent-alt': colors.accentAlt,
    '--color-success': colors.success,
    '--color-warning': colors.warning,
    '--color-danger': colors.danger,
    '--color-neutral-1': colors.neutral1,
    '--spacing-1': theme.spacing[1],
    '--spacing-2': theme.spacing[2],
    '--spacing-3': theme.spacing[3],
    '--spacing-4': theme.spacing[4],
    '--spacing-5': theme.spacing[5],
    '--spacing-6': theme.spacing[6],
    '--border-radius-base': theme.borderRadius.base,
    '--border-radius-lg': theme.borderRadius.lg,
    '--shadow-card': theme.shadows.card,
    '--shadow-elevated': theme.shadows.elevated,
    '--font-family-base': theme.typography.fontFamily.base,
    '--duration-fast': theme.animation.duration.fast,
    '--duration-base': theme.animation.duration.base,
    '--left-rail-width': theme.layout.leftRailWidth,
    '--top-bar-height': theme.layout.topBarHeight,
  }
}

// Microinteractions configuration
export const microInteractions = {
  slideOver: {
    duration: theme.animation.duration.base,
    easing: theme.animation.easing.easeOut,
  },
  rowHover: {
    duration: theme.animation.duration.fast,
    transform: 'translateY(-1px)',
    shadow: theme.shadows.elevated,
  },
  acceptSuggestion: {
    duration: '160ms',
    highlightColor: theme.colors.success,
  },
  dragAndDrop: {
    borderStyle: 'dashed',
    borderColor: theme.colors.accentPrimary,
  },
  undoSnackbar: {
    position: 'bottom-left',
    duration: 6000, // 6 seconds
    backgroundColor: theme.colors.card,
    textColor: theme.colors.textPrimary,
  }
}

// Accessibility configuration
export const accessibility = {
  focusOutline: {
    color: theme.colors.accentPrimary,
    width: '2px',
    offset: '2px',
    style: 'solid',
  },
  minTouchTarget: '44px',
  contrastRatios: {
    normal: 4.5,  // WCAG AA
    large: 3,     // WCAG AA for large text
    enhanced: 7,  // WCAG AAA
  },
  reducedMotion: {
    duration: '0.01ms',
    easing: 'linear',
  }
}

// Component-specific design tokens
export const components = {
  kpiCard: {
    padding: theme.spacing[6],
    borderRadius: theme.borderRadius.lg,
    backgroundColor: theme.colors.card,
    borderColor: theme.colors.neutral1,
    shadow: theme.shadows.card,
  },
  button: {
    primary: {
      backgroundColor: theme.colors.accentPrimary,
      color: theme.colors.textPrimary,
      borderRadius: theme.borderRadius.base,
      padding: `${theme.spacing[3]} ${theme.spacing[6]}`,
      fontSize: theme.typography.fontSize.body,
      fontWeight: theme.typography.fontWeight.medium,
    },
    secondary: {
      backgroundColor: 'transparent',
      color: theme.colors.textMuted,
      borderColor: theme.colors.neutral1,
      borderWidth: '1px',
    }
  },
  table: {
    headerBackgroundColor: theme.colors.surface,
    rowBorderColor: theme.colors.neutral1,
    rowHoverBackgroundColor: theme.colors.surface,
    selectedRowBackgroundColor: `${theme.colors.accentPrimary}20`, // 20% opacity
  },
  slideOver: {
    width: '500px',
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.neutral1,
    shadow: theme.shadows.elevated,
  }
}