/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Design tokens from specification
      colors: {
        // Background colors (dark-first)
        'bg': '#0B0F13',
        'surface': '#0F1418',
        'card': '#13171B',

        // Text colors
        'text-primary': '#E6EEF3',
        'text-muted': '#A8B3BD',

        // Accent colors
        'accent-primary': '#6C8EF5',  // indigo
        'accent-alt': '#08A6A6',      // teal

        // Semantic colors
        'success': '#16A34A',
        'warning': '#F59E0B',
        'danger': '#EF4444',

        // Neutral
        'neutral-1': '#0C1114',

        // Light mode overrides (when needed)
        'light': {
          'bg': '#FFFFFF',
          'surface': '#F8FAFC',
          'card': '#FFFFFF',
          'text-primary': '#1F2937',
          'text-muted': '#6B7280',
        }
      },

      // Typography
      fontFamily: {
        'inter': ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        'sans': ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },

      fontSize: {
        'xs': ['12px', '16px'],
        'sm': ['14px', '20px'],
        'base': ['16px', '24px'],
        'lg': ['18px', '28px'],
        'xl': ['20px', '28px'],
        '2xl': ['24px', '32px'],
        '3xl': ['28px', '36px'],
      },

      // Spacing (4px base scale)
      spacing: {
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
        '10': '40px',
        '12': '48px',
        '16': '64px',
        '20': '80px',
        '24': '96px',
      },

      // Border radius
      borderRadius: {
        'sm': '4px',
        'DEFAULT': '8px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
      },

      // Shadows (elevated for dark mode)
      boxShadow: {
        'card': '0 6px 18px rgba(2, 6, 23, 0.4)',
        'elevated': '0 10px 25px rgba(2, 6, 23, 0.5)',
        'focus': '0 0 0 2px #6C8EF5',
      },

      // Animation timings
      transitionDuration: {
        '150': '150ms',
        '200': '200ms',
        '300': '300ms',
      },

      // Z-index scale
      zIndex: {
        'modal': '1000',
        'overlay': '900',
        'dropdown': '800',
        'header': '700',
        'sidebar': '600',
      },

      // Layout widths
      maxWidth: {
        'sidebar': '256px',
        'content': '1400px',
      },

      minWidth: {
        'sidebar': '200px',
      },

      // Grid template columns for dashboard
      gridTemplateColumns: {
        'dashboard': 'minmax(256px, 300px) 1fr minmax(0, 400px)',
        'parcels': 'minmax(256px, 300px) 1fr minmax(400px, 500px)',
      },
    },
  },
  plugins: [
    // Form plugin for better form styling
    require('@tailwindcss/forms')({
      strategy: 'class',
    }),
  ],
}