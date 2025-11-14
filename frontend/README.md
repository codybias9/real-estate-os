# Real Estate OS - Frontend

Next.js frontend application for the Real Estate Operating System.

## Overview

This is a modern, responsive web application built with Next.js 14, TypeScript, and Tailwind CSS. It provides a user interface for property discovery, enrichment, scoring, and collaboration.

## Features

### Property Management
- **Property List View**: Browse and filter properties with pagination
- **Property Details**: Comprehensive property information drawer
- **Score Visualization**: Interactive score breakdown with explainability
- **Real-time Updates**: SSE (Server-Sent Events) for live timeline updates

### Collaboration
- **Timeline**: Property activity stream with system and user events
- **Comments**: Add comments to properties
- **Notes**: Create and edit markdown-supported notes
- **Real-time Sync**: Live updates when team members add events

### Filtering & Search
- **State Filter**: Filter by property lifecycle state
- **Score Range**: Filter by investment score range
- **Search**: Search by address or APN
- **Multi-select**: Batch actions on selected properties

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Data Fetching**: React Query (@tanstack/react-query)
- **HTTP Client**: Axios
- **Real-time**: Server-Sent Events (SSE)
- **Markdown**: react-markdown
- **Notifications**: react-hot-toast
- **Testing**: Jest + React Testing Library

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Real Estate OS API running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Environment Variables

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm run start
```

### Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js app router pages
│   │   ├── layout.tsx       # Root layout with providers
│   │   ├── page.tsx         # Home page (property dashboard)
│   │   ├── providers.tsx    # React Query provider
│   │   └── globals.css      # Global styles
│   ├── components/          # React components
│   │   ├── Header.tsx       # App header with navigation
│   │   ├── PropertyList.tsx # Property list with filters
│   │   ├── PropertyCard.tsx # Property card component
│   │   ├── PropertyDrawer.tsx # Property detail drawer
│   │   ├── ScoreVisualization.tsx # Score breakdown
│   │   ├── Timeline.tsx     # Timeline with SSE
│   │   └── LoadingSpinner.tsx # Loading indicator
│   ├── hooks/               # Custom React hooks
│   │   ├── use-properties.ts # Property queries
│   │   ├── use-timeline.ts   # Timeline queries + SSE
│   │   └── use-outreach.ts   # Outreach queries
│   ├── lib/                 # Utilities and clients
│   │   ├── api-client.ts    # API client with SSE support
│   │   └── utils.ts         # Utility functions
│   ├── types/               # TypeScript types
│   │   ├── property.ts      # Property domain types
│   │   ├── timeline.ts      # Timeline event types
│   │   └── outreach.ts      # Outreach campaign types
│   └── __tests__/           # Jest tests
│       ├── components/      # Component tests
│       ├── hooks/           # Hook tests
│       └── lib/             # Utility tests
├── public/                  # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── jest.config.js
└── next.config.js
```

## Key Components

### PropertyList

Main property list view with filtering, pagination, and search.

```tsx
<PropertyList onPropertySelect={(id) => console.log(id)} />
```

### PropertyDrawer

Slide-over drawer showing property details with tabs:
- Overview: Property and owner details
- Score: Investment score breakdown
- Timeline: Activity stream with real-time updates
- Outreach: Campaign status

```tsx
<PropertyDrawer
  propertyId="prop-123"
  open={true}
  onClose={() => setOpen(false)}
/>
```

### Timeline

Real-time activity stream with SSE support.

```tsx
<Timeline propertyId="prop-123" />
```

### ScoreVisualization

Interactive score breakdown with feature weights and explanations.

```tsx
<ScoreVisualization
  score={78}
  scoreResult={scoreResult}
  isLoading={false}
/>
```

## API Integration

### API Client

The `ApiClient` class provides type-safe methods for all backend endpoints:

```typescript
import { apiClient } from '@/lib/api-client';

// Get properties with filters
const properties = await apiClient.getProperties({
  state: [PropertyState.SCORED],
  min_score: 70,
  page: 1,
  per_page: 20,
});

// Get single property
const property = await apiClient.getProperty('prop-123');

// Subscribe to timeline SSE
const eventSource = apiClient.subscribeToTimeline(
  'prop-123',
  (event) => console.log('New event:', event),
  (error) => console.error('SSE error:', error)
);

// Don't forget to close when done
eventSource.close();
```

### React Query Hooks

Custom hooks abstract data fetching with caching and optimistic updates:

```typescript
import { useProperties, useProperty, useTimeline } from '@/hooks';

function MyComponent() {
  // Paginated properties with filters
  const { data, isLoading } = useProperties({ min_score: 70 });

  // Single property
  const { data: property } = useProperty('prop-123');

  // Timeline with real-time updates
  const { data: events } = useTimeline('prop-123');
  const { connected } = useTimelineSubscription('prop-123');

  // Mutations
  const addComment = useAddComment();
  addComment.mutate({
    property_id: 'prop-123',
    content: 'Great property!',
  });
}
```

## Real-time Updates

The frontend uses Server-Sent Events (SSE) for real-time updates:

### Timeline SSE

```typescript
const { connected, error } = useTimelineSubscription(propertyId);

// 'connected' is true when SSE connection is active
// 'error' contains error message if connection fails
// Timeline events are automatically added to React Query cache
```

### State SSE

```typescript
const eventSource = apiClient.subscribeToState(
  propertyId,
  (newState) => console.log('State changed to:', newState),
  (error) => console.error('SSE error:', error)
);
```

## Testing

### Component Tests

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { PropertyCard } from '@/components/PropertyCard';

test('renders property address', () => {
  render(<PropertyCard property={mockProperty} onClick={jest.fn()} />);
  expect(screen.getByText(/123 Main St/i)).toBeInTheDocument();
});
```

### Hook Tests

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useProperties } from '@/hooks';

test('fetches properties', async () => {
  const { result } = renderHook(() => useProperties());
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data).toBeDefined();
});
```

## Design Decisions

### Why Next.js App Router?

- Server Components for better performance
- Built-in TypeScript support
- File-based routing
- API route rewrites for CORS

### Why React Query?

- Automatic caching and refetching
- Optimistic updates
- SSE integration with cache updates
- Loading and error states

### Why SSE over WebSockets?

- Simpler server implementation
- Unidirectional updates (server → client)
- Better browser support
- Automatic reconnection

### Why Tailwind CSS?

- Utility-first approach
- Excellent TypeScript support
- Smaller bundle size
- Consistent design system

## Performance

### Optimizations

- React Query caching (30s stale time)
- Code splitting with Next.js dynamic imports
- Image optimization with Next.js Image component
- Lazy loading for drawer content
- Optimistic UI updates

### Metrics

- **First Load**: < 500ms (target)
- **Time to Interactive**: < 2s (target)
- **Bundle Size**: < 300KB (gzipped)

## Accessibility

- Semantic HTML elements
- ARIA labels for interactive elements
- Keyboard navigation support
- Focus management for modals/drawers
- Screen reader support

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Future Enhancements

### PR12 (Auth & Tenancy)
- JWT authentication with Auth0
- User profile dropdown
- Tenant switcher
- Protected routes

### PR13 (Observability)
- Error boundary for component errors
- Performance monitoring
- User analytics

### PR14 (Performance)
- Redis caching layer
- Infinite scroll for property list
- Virtual scrolling for large lists

## Contributing

### Code Style

- Follow TypeScript strict mode
- Use functional components with hooks
- Prefer composition over inheritance
- Write tests for all components

### Commit Messages

```
feat(component): Add PropertyDrawer with tabs
fix(timeline): Fix SSE reconnection logic
test(utils): Add tests for formatCurrency
docs(readme): Update API client documentation
```

## License

Proprietary - Real Estate OS

## Support

For issues or questions, contact the development team or open an issue in the repository.
