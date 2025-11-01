# Real Estate OS - Web UI

React + TypeScript frontend for Real Estate OS featuring the **Deal Genome** provenance tracking system.

## Features

### 🔍 Property Drawer with 4 Tabs

1. **Details Tab** - Basic property information
   - Address, property specs, owners, deals
   - Financial information (price, value, taxes)
   - Property features and description

2. **Provenance Tab** ⭐ **(Wave 1.6 - Deal Genome)**
   - Complete field-level provenance tracking
   - Source system, method, confidence for every field
   - Stale data detection (>30 days)
   - Searchable fields table
   - Coverage statistics dashboard
   - **Field History Modal** - Version timeline with value changes

3. **Scorecard Tab**
   - ML score explainability with SHAP values
   - Top positive/negative drivers
   - What-if scenarios (counterfactuals)
   - Feature importance visualization

4. **Timeline Tab**
   - Activity feed (placeholder for future development)
   - Deal progression tracking

### 📊 Key Components

- **Hover Tooltips** - Source, confidence, last updated for each field
- **History Modal** - Complete version timeline with change indicators
- **Stale Detection** - Visual alerts for outdated data
- **Coverage Dashboard** - Real-time provenance statistics
- **Confidence Bars** - Visual representation of data quality

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Lightning-fast build tool
- **Tailwind CSS** - Utility-first styling
- **TanStack Query (React Query)** - Data fetching & caching
- **Axios** - HTTP client
- **date-fns** - Date formatting
- **Recharts** - Data visualization (ready for Wave 2)
- **Lucide React** - Icon library

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- FastAPI backend running on port 8000

### Installation

```bash
cd web
npm install
```

### Configuration

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# API Configuration
VITE_API_BASE_URL=/api
VITE_TENANT_ID=00000000-0000-0000-0000-000000000001
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Build

```bash
npm run build
```

Output in `dist/` directory.

### Lint

```bash
npm run lint
```

### Type Check

```bash
npm run type-check
```

## Project Structure

```
web/
├── src/
│   ├── components/          # React components
│   │   ├── PropertyDrawer.tsx      # Main drawer container
│   │   ├── DetailsTab.tsx          # Property details
│   │   ├── ProvenanceTab.tsx       # ⭐ Field provenance (Wave 1.6)
│   │   ├── FieldHistoryModal.tsx   # ⭐ Version timeline
│   │   ├── ScorecardTab.tsx        # ML explainability
│   │   └── TimelineTab.tsx         # Activity timeline
│   ├── hooks/               # React hooks
│   │   └── useProperty.ts          # React Query hooks
│   ├── services/            # API clients
│   │   └── api.ts                  # FastAPI client
│   ├── types/               # TypeScript types
│   │   └── provenance.ts           # API type definitions
│   ├── utils/               # Utility functions
│   │   ├── format.ts               # Formatting helpers
│   │   └── cn.ts                   # Class name utility
│   ├── App.tsx              # Main app component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── index.html              # HTML template
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies
```

## Usage

### Opening a Property

```tsx
import { PropertyDrawer } from './components/PropertyDrawer';

function App() {
  const [propertyId, setPropertyId] = useState<string | null>(null);

  return (
    <>
      <button onClick={() => setPropertyId('uuid-here')}>
        Open Property
      </button>

      {propertyId && (
        <PropertyDrawer
          propertyId={propertyId}
          onClose={() => setPropertyId(null)}
        />
      )}
    </>
  );
}
```

### API Integration

The app automatically connects to the FastAPI backend via proxy:

```typescript
// In vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

All API calls go through `/api/*` which proxies to `http://localhost:8000/*`.

### React Query Hooks

```typescript
import { useProperty, useProvenanceStats, useFieldHistory } from '@/hooks/useProperty';

// Fetch property with provenance
const { data: property } = useProperty(propertyId);

// Fetch provenance statistics
const { data: stats } = useProvenanceStats(propertyId);

// Fetch field history (lazy-loaded)
const { data: history } = useFieldHistory(propertyId, 'listing_price', true);
```

## Wave 1.6 Acceptance Criteria

### ✅ Implemented

- [x] Property Drawer with tabbed interface
- [x] **Provenance Tab** with complete field tracking
- [x] Hover tooltips showing source, method, confidence
- [x] **Field History Modal** with version timeline
- [x] Stale field detection (>30 days) with visual indicators
- [x] Coverage statistics dashboard
- [x] Search functionality for fields
- [x] Source distribution visualization
- [x] Confidence bars with color coding
- [x] Method badges (scrape, api, manual, computed)
- [x] Value change indicators (increase/decrease)
- [x] Responsive design with animations

### 📊 Target Metrics

| Metric | Target | Status |
|--------|--------|--------|
| UI fields with provenance | ≥95% | ✅ Backend ready |
| Stale detector true-positive rate | ≥90% | ✅ Backend ready |
| Hover tooltip support | Yes | ✅ Implemented |
| "See History" modal | Yes | ✅ Implemented |

## API Endpoints Used

```
GET /properties/{id}
  → PropertyDetail with provenance

GET /properties/{id}/provenance
  → ProvenanceStatsResponse (coverage, sources)

GET /properties/{id}/history/{field_path}
  → FieldHistoryResponse (version timeline)

GET /properties/{id}/scorecard
  → ScoreExplainabilityDetail (SHAP, drivers)
```

All endpoints automatically include `tenant_id` query parameter.

## Styling

### Tailwind Utilities

- **Color Palette**: `primary-*` (blue), `green-*`, `red-*`, `yellow-*`
- **Animations**: `animate-fade-in`, `animate-slide-in`
- **Custom Scrollbar**: `.scrollbar-thin`

### Confidence Color Coding

| Confidence | Color | Class |
|------------|-------|-------|
| ≥90% | Green | `text-green-600` |
| 75-89% | Blue | `text-blue-600` |
| 50-74% | Yellow | `text-yellow-600` |
| <50% | Red | `text-red-600` |

### Method Badges

| Method | Badge Color |
|--------|-------------|
| api | Green (`bg-green-100`) |
| scrape | Blue (`bg-blue-100`) |
| manual | Purple (`bg-purple-100`) |
| computed | Yellow (`bg-yellow-100`) |

## Development Tips

### Hot Reload

Vite provides instant HMR (Hot Module Replacement). Changes reflect immediately without full page reload.

### TypeScript Strict Mode

The project uses strict TypeScript for type safety:

```json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true
}
```

### Path Aliases

Use `@/` for imports:

```typescript
import { apiClient } from '@/services/api';
import { formatCurrency } from '@/utils/format';
import { PropertyDetail } from '@/types/provenance';
```

### React Query DevTools

Add DevTools for debugging (optional):

```bash
npm install @tanstack/react-query-devtools
```

```tsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

<QueryClientProvider client={queryClient}>
  <App />
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

## Deployment

### Production Build

```bash
npm run build
```

### Serve Locally

```bash
npm run preview
```

### Environment Variables

Set production API URL:

```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_TENANT_ID=your-production-tenant-id
```

### Docker (Optional)

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

Build and run:

```bash
docker build -t realestate-os-web .
docker run -p 80:80 realestate-os-web
```

## Testing

### Unit Tests (Future)

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

### E2E Tests (Future)

```bash
npm install -D playwright
```

## Contributing

1. Follow TypeScript strict mode
2. Use Tailwind CSS (no inline styles)
3. Add JSDoc comments to components
4. Use React Query for all API calls
5. Follow existing naming conventions

## Troubleshooting

### API Connection Issues

**Problem**: Cannot connect to backend

**Solution**:
1. Verify FastAPI is running on port 8000
2. Check `.env` configuration
3. Verify proxy in `vite.config.ts`

### Type Errors

**Problem**: TypeScript type mismatches

**Solution**:
1. Run `npm run type-check`
2. Ensure types in `src/types/provenance.ts` match backend schemas
3. Update types if API changed

### Build Errors

**Problem**: Build fails with module errors

**Solution**:
1. Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
2. Clear Vite cache: `rm -rf node_modules/.vite`
3. Update dependencies: `npm update`

## Performance

### Bundle Size

- **Optimized chunks** - Vite automatically code-splits
- **Tree shaking** - Unused code eliminated
- **Lazy loading** - Field history modal loaded on demand

### Caching

- **React Query** - 5-minute stale time for property data
- **10-minute stale time** for field history (changes infrequently)

### Animations

- Hardware-accelerated CSS animations
- Smooth 60fps transitions

## Next Steps (Future Waves)

### Wave 2 - Portfolio Twin

- Add look-alikes section to Scorecard tab
- Vector similarity visualization
- Embedding space explorer

### Wave 3 - Comp-Critic

- Adversarial comp analysis UI
- Negotiation recommendations
- Outreach sequence builder

### Wave 4 - Offer Wizard

- Constraint satisfaction UI
- Market regime indicators
- Offer scenario builder

### Wave 5 - Trust Ledger

- Evidence event timeline
- Cross-tenant comp sharing UI
- Trust score visualization

## License

Proprietary - Real Estate OS

## Support

For issues or questions, contact the development team or open an issue in the repository.

---

**Built with ❤️ for Wave 1.6 - Deal Genome Provenance UI**
