---
name: nextjs-app
description: Build production-grade Next.js 14+ applications with App Router, TypeScript, Tailwind CSS, and shadcn/ui. Use when creating pages, components, layouts, API routes, or client/server component architecture.
---

# Next.js Application Development

Build modern, performant React applications with Next.js 14+ App Router.

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # App Router pages
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── globals.css         # Global styles
│   │   ├── search/
│   │   │   └── page.tsx        # Search results
│   │   ├── analysis/
│   │   │   └── [id]/
│   │   │       └── page.tsx    # Analysis detail
│   │   └── settings/
│   │       └── page.tsx        # API key configuration
│   ├── components/
│   │   ├── ui/                 # shadcn/ui base components
│   │   ├── news/               # News-specific components
│   │   │   ├── article-card.tsx
│   │   │   ├── comparison-view.tsx
│   │   │   ├── bias-meter.tsx
│   │   │   └── fact-panel.tsx
│   │   ├── layout/             # Layout components
│   │   └── settings/           # Settings components
│   ├── hooks/                  # Custom React hooks
│   │   ├── use-search.ts
│   │   ├── use-websocket.ts
│   │   └── use-api-keys.ts
│   ├── lib/                    # Utilities
│   │   ├── api.ts              # API client (fetch wrapper)
│   │   ├── utils.ts            # General utilities
│   │   └── constants.ts
│   └── types/                  # TypeScript type definitions
│       ├── article.ts
│       ├── analysis.ts
│       └── api.ts
├── public/
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Key Patterns

### Server vs Client Components
```tsx
// Server Component (default) - for data fetching, SEO
export default async function SearchPage({ searchParams }) {
  const data = await fetchResults(searchParams.q);
  return <ResultsList data={data} />;
}

// Client Component - for interactivity
"use client";
export function SearchForm() {
  const [query, setQuery] = useState("");
  // ...
}
```

### API Client
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

### WebSocket Hook
```typescript
export function useWebSocket(taskId: string) {
  const [status, setStatus] = useState<TaskStatus>("pending");
  const [results, setResults] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws/tasks/${taskId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      if (data.results) setResults(data.results);
    };
    return () => ws.close();
  }, [taskId]);

  return { status, results };
}
```

## Styling with Tailwind + shadcn/ui

- Use `shadcn/ui` for base components (Button, Card, Dialog, etc.)
- Initialize with `npx shadcn@latest init`
- Add components: `npx shadcn@latest add button card dialog`
- Customize theme in `tailwind.config.ts` using CSS variables
- Use `cn()` utility for conditional class merging

## Best Practices

- **TypeScript strict mode**: Enable in `tsconfig.json`
- **Server Components by default**: Only use `"use client"` when needed
- **Loading states**: Use `loading.tsx` and Suspense boundaries
- **Error boundaries**: Use `error.tsx` for graceful error handling
- **Image optimization**: Use `next/image` for all images
- **Environment variables**: `NEXT_PUBLIC_` prefix for client-side vars
- **SEO**: Use `generateMetadata` for dynamic meta tags
- **Standalone output**: Set `output: "standalone"` in `next.config.js` for Docker
