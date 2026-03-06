# Frontend Spec — NFL QB Personnel Analysis

**Stack:** Next.js 14 (App Router), React, Tailwind CSS, Recharts  
**API base URL:** `http://localhost:8000` (local), env var for production  
**Deploy target:** Vercel  

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout, nav, global styles
│   ├── page.tsx                # Redirects to /dashboard
│   ├── dashboard/
│   │   └── page.tsx            # QB Dashboard page
│   └── trends/
│       └── page.tsx            # League Trends page
├── components/
│   ├── nav/
│   │   └── Navbar.tsx          # Top nav with links to both pages
│   ├── dashboard/
│   │   ├── QBSelector.tsx      # Dropdown to select a QB
│   │   ├── SeasonFilter.tsx    # 2022 / 2023 / 2024 / Career buttons
│   │   ├── StatsGrid.tsx       # 4-card summary (plays, EPA, success rate, CPOE)
│   │   ├── MatchupScatter.tsx  # Scatter plot: volume vs EPA by matchup
│   │   ├── TopMatchups.tsx     # Bar chart: top 5 matchups by EPA/play
│   │   └── MatchupTable.tsx    # Full sortable table of all matchups
│   └── trends/
│       ├── MatchupUsageChart.tsx  # Line chart: usage % by matchup over seasons
│       └── TrendsTable.tsx        # Sortable table of all matchup trends
├── lib/
│   └── api.ts                  # Typed fetch functions for all API endpoints
├── types/
│   └── index.ts                # TypeScript interfaces matching Pydantic models
└── .env.local                  # NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Page 1: QB Dashboard (`/dashboard`)

**Layout:** Full-width, dark header, white content area

**Controls (top of page):**
- QB selector dropdown — populated from `GET /qbs`, shows QB name, sorted by career plays desc
- Season filter — pill buttons: `2022` `2023` `2024` `Career`
- Min plays toggle — `20+` / `50+` / `100+` (filters matchup rows client-side)

**Stats Grid (4 cards below controls):**  
Pulls from the selected QB's stats rows, aggregated client-side:
- Total Plays
- EPA/Play (weighted average)
- Success Rate (weighted average)
- Pass Attempts

**Scatter Plot — Matchup Efficiency (`MatchupScatter`):**
- X-axis: Play volume (play_count)
- Y-axis: EPA per play
- Each point = one personnel matchup
- Color: green if above 0 EPA, red if below
- Tooltip: matchup name, play count, EPA/play, success rate
- Reference line at y=0

**Bar Chart — Top 5 Matchups (`TopMatchups`):**
- Horizontal bar chart
- Top 5 matchups by EPA/play (filtered by min plays threshold)
- Color-coded by offense personnel group

**Matchup Table (`MatchupTable`):**
- Sortable by any column
- Columns: Matchup, Plays, EPA/Play, Success Rate, Pass Att, Sacks, Scrambles, Avg CPOE
- Highlight rows that meet `meets_starter_threshold`
- Pagination at 10 rows

---

## Page 2: League Trends (`/trends`)

**Layout:** Same header/nav as dashboard

**Controls:**
- Season filter — same pill buttons as dashboard, defaults to showing all seasons

**Line Chart — Personnel Usage Over Time (`MatchupUsageChart`):**
- X-axis: Season (2022, 2023, 2024)
- Y-axis: Usage % (0-100)
- One line per matchup type
- Only show top 6 matchups by total volume to avoid clutter
- Tooltip: matchup, season, usage %, EPA/play

**Trends Table (`TrendsTable`):**
- Sortable by any column
- Columns: Matchup, Season, Usage %, League EPA/Play, # QBs, Pass Rate, YoY Usage Change
- Color-code YoY change column: green = up, red = down, gray = no prior year

---

## `lib/api.ts` — Typed API Functions

```typescript
const API = process.env.NEXT_PUBLIC_API_URL

export async function getQBs(): Promise<QB[]>
export async function getQBStats(qbId: string, season?: string, minPlays?: number): Promise<QBStats[]>
export async function getTrends(season?: string): Promise<LeagueTrend[]>
export async function getMatchup(matchup: string, season?: string): Promise<QBStats[]>
```

---

## `types/index.ts` — TypeScript Interfaces

Mirror the Pydantic models exactly:

```typescript
interface QB {
  qb_id: string
  qb_name: string | null
  career_plays: number
  career_epa_per_play: number
  career_success_rate: number
  is_starter: boolean
  seasons_played: number
}

interface QBStats {
  qb_id: string
  qb_name: string | null
  season: string
  team: string | null
  personnel_matchup: string
  play_count: number
  epa_per_play: number
  success_rate: number
  pass_attempts: number
  sacks: number
  scrambles: number
  avg_cpoe: number | null
  meets_min_threshold: boolean
  meets_starter_threshold: boolean
}

interface LeagueTrend {
  season: string
  personnel_matchup: string
  league_play_count: number
  usage_pct: number
  league_epa_per_play: number
  usage_rank: number
  usage_pct_change_yoy: number | null
}
```

---

## Vercel Deployment

1. Push `frontend/` to GitHub (already in repo)
2. Connect repo to Vercel at vercel.com
3. Set root directory to `frontend/`
4. Add env var: `NEXT_PUBLIC_API_URL` pointing to deployed API URL
5. API needs to be deployed separately (Railway or Render) before frontend deploy works end to end

---

## Claude Code Prompt

When ready, give Claude Code this prompt:

> "Build the Next.js frontend according to the spec in FRONTEND_SPEC.md. Initialize a Next.js 14 app with TypeScript and Tailwind in the `frontend/` directory. Install Recharts. Build in this order: (1) types/index.ts, (2) lib/api.ts, (3) Navbar, (4) QB Dashboard page with all components, (5) League Trends page with all components. Use `http://localhost:8000` as the API base URL via a `NEXT_PUBLIC_API_URL` env var. After scaffolding, run the dev server and confirm it starts without errors. Do not deploy yet."

---

## Local Development Notes

- FastAPI runs on `http://localhost:8000`
- Next.js dev server runs on `http://localhost:3000`
- Both must be running simultaneously when developing locally
- Start the API first: `uvicorn api.app:app --reload` from project root
- Start the frontend: `npm run dev` from `frontend/` directory

---

## API Endpoints Reference

| Method | Endpoint | Used By |
|--------|----------|---------|
| `GET /qbs` | All QBs with career aggregates | QBSelector dropdown |
| `GET /qbs/{qb_id}/stats` | QB stats by matchup | Dashboard charts + table |
| `GET /trends` | League-wide personnel trends | Trends page |
| `GET /matchup/{matchup}` | All QBs for a specific matchup | (future enhancement) |

Query params:
- `/qbs/{qb_id}/stats?season=2024&min_plays=20`
- `/trends?season=2024`
