# Alabama Auction Watcher - Desktop Frontend

Modern desktop-first application built with React, TypeScript, and Electron for monitoring and analyzing Alabama tax auction properties.

## Features

- **Desktop-first UI** with dark mode as default
- **Progressive disclosure** design pattern
- **Keyboard-driven** power user workflows
- **Real-time data** from FastAPI backend
- **AI-powered** property analysis and suggestions
- **Map integration** with clustering and filtering
- **CSV import/export** with column mapping
- **Local persistence** with optional cloud sync

## Tech Stack

- **Frontend**: React 18 + TypeScript
- **Desktop**: Electron
- **Styling**: Tailwind CSS with custom design tokens
- **Build Tool**: Vite
- **State Management**: React Context + useReducer
- **Data Fetching**: Axios with caching
- **Maps**: Mapbox GL JS
- **Charts**: Plotly.js
- **Local Storage**: IndexedDB via LocalForage
- **UI Components**: Custom components following design specification

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on `http://localhost:8001`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Start Electron in development
npm run electron:dev

# Build for production
npm run build

# Package desktop app
npm run electron:pack
```

### Development Scripts

- `npm run dev` - Start Vite dev server
- `npm run electron:dev` - Start Electron with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues

## Architecture

### Directory Structure

```
src/
├── components/          # Reusable UI components
│   ├── Layout.tsx      # Main application layout
│   ├── LeftRail.tsx    # Navigation sidebar
│   ├── TopBar.tsx      # Header with search and filters
│   └── ...
├── pages/              # Route components
│   ├── Dashboard.tsx   # KPI cards and overview
│   ├── Parcels.tsx     # Main property table
│   ├── Map.tsx         # Spatial property view
│   └── ...
├── lib/                # Utilities and services
│   ├── api.ts          # Backend API client
│   ├── context.tsx     # Global state management
│   ├── db.ts           # Local storage wrapper
│   └── ...
└── styles/             # Global styles and tokens
    └── index.css       # Tailwind + custom styles
```

### Design Tokens

The app uses a comprehensive design token system defined in `tailwind.config.js`:

- **Colors**: Dark-first palette with semantic naming
- **Typography**: Inter font with consistent scale
- **Spacing**: 4px base scale for consistent layouts
- **Shadows**: Elevated shadows optimized for dark backgrounds
- **Animations**: Smooth transitions with performance focus

### State Management

Global application state is managed through React Context with useReducer:

- **Theme**: Light/dark mode toggle
- **Selected Properties**: Multi-select state across components
- **Filters**: Shared filter state between components
- **Loading/Error**: Global loading and error states

### API Integration

The frontend connects to the existing FastAPI backend:

- **Base URL**: `http://localhost:8001/api/v1/`
- **Authentication**: JWT tokens (when implemented)
- **Caching**: Intelligent caching with TTL
- **Error Handling**: Comprehensive error boundaries

## Keyboard Shortcuts

- `/` - Focus global search
- `Cmd/Ctrl+I` - Import CSV
- `Cmd/Ctrl+E` - Export data
- `Cmd/Ctrl+1-3` - Navigate between main views
- `Cmd/Ctrl+T` - Open triage queue
- `Cmd/Ctrl+/` - Toggle search
- `Cmd/Ctrl+Shift+T` - Toggle theme
- `Esc` - Close modals/slide-overs

## Data Models

TypeScript interfaces match the existing SQLAlchemy models:

- **Property**: Core property data with investment scores
- **County**: Alabama county information
- **AISuggestion**: AI-generated property corrections
- **UserProfile**: Application user preferences
- **PropertyApplication**: Property application tracking

## Contributing

1. Follow the existing component patterns
2. Use TypeScript for all new code
3. Follow the design token system for styling
4. Add proper accessibility attributes
5. Test keyboard navigation
6. Maintain dark-mode-first approach

## Build & Deployment

### Development Build
```bash
npm run build
```

### Desktop Distribution
```bash
# Build app packages for current platform
npm run electron:dist

# Output will be in dist/ directory
```

### Supported Platforms
- Windows (NSIS installer)
- macOS (DMG)
- Linux (AppImage)

## Performance

- **Bundle splitting** for optimal loading
- **Lazy loading** of heavy components
- **Virtual scrolling** for large data sets
- **Intelligent caching** with memory management
- **Background workers** for heavy computations