// Prototype — not production code

interface ComponentCard {
  name: string
  description: string
  status: 'placeholder' | 'in-progress' | 'done'
  phase: string
}

const COMPONENTS: ComponentCard[] = [
  {
    name: 'InquiryTrace',
    description:
      'Visualises the multi-stage recall pipeline: BM25 candidates → entity-hop → RRF re-rank → MMR final set. Consumes the trace object from the recall_with_trace MCP tool.',
    status: 'placeholder',
    phase: 'Phase C / Cycle U.1',
  },
  {
    name: 'KnotView',
    description:
      'Renders entity strands and cross-strand crossings as an interactive graph. Shows bead type (semantic / procedural / episodic), importance score, and session/event date.',
    status: 'placeholder',
    phase: 'Phase C / Cycle U.2',
  },
  {
    name: 'MemoryTimeTravel',
    description:
      'Timeline scrubber over a conversation\'s memory state. Replays which beads were active at each session boundary. Depends on versioned KnotData snapshots.',
    status: 'placeholder',
    phase: 'Phase D / Cycle U.3',
  },
  {
    name: 'PromiseLedger',
    description:
      'Displays procedural commitments extracted from conversations (promises, tasks, follow-ups) with fulfilment status and source turn references.',
    status: 'placeholder',
    phase: 'Phase D / Cycle U.4',
  },
]

const STATUS_CLASSES: Record<ComponentCard['status'], string> = {
  placeholder: 'bg-gray-100 text-gray-500 border-gray-200',
  'in-progress': 'bg-yellow-50 text-yellow-700 border-yellow-200',
  done: 'bg-green-50 text-green-700 border-green-200',
}

const STATUS_LABEL: Record<ComponentCard['status'], string> = {
  placeholder: 'Placeholder',
  'in-progress': 'In Progress',
  done: 'Done',
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Knot UX Prototype</h1>
            <p className="text-sm text-slate-500 mt-0.5">ai-knot · Cycle U.scaffold</p>
          </div>
          <span className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 border border-amber-200">
            Prototype — not production
          </span>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-6 py-10">
        <section className="mb-8">
          <h2 className="text-base font-medium text-slate-700 mb-1">Upcoming components</h2>
          <p className="text-sm text-slate-500">
            Each card is a placeholder for a future UI component. Mock data lives in{' '}
            <code className="font-mono text-xs bg-slate-100 px-1 py-0.5 rounded">
              src/data/
            </code>
            . No real backend is connected.
          </p>
        </section>

        <div className="grid gap-4 sm:grid-cols-2">
          {COMPONENTS.map((c) => (
            <article
              key={c.name}
              className={`rounded-xl border p-5 flex flex-col gap-3 ${STATUS_CLASSES[c.status]}`}
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-mono text-sm font-semibold">{c.name}</h3>
                <span className="text-xs font-medium whitespace-nowrap opacity-70">
                  {STATUS_LABEL[c.status]}
                </span>
              </div>
              <p className="text-sm leading-relaxed opacity-80">{c.description}</p>
              <p className="text-xs font-mono opacity-60 mt-auto">{c.phase}</p>
            </article>
          ))}
        </div>

        {/* Mock data info */}
        <section className="mt-10 rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Mock data</h2>
          <ul className="space-y-2 text-sm text-slate-600">
            <li>
              <code className="font-mono text-xs bg-slate-100 px-1 py-0.5 rounded">
                src/data/mock-trace.json
              </code>
              {' — '}3 synthetic recall traces (FACTUAL / AGGREGATIONAL / EXPLORATORY). Entities:
              Sarah, Tom, Apollo (dog), Camping Trip.
            </li>
            <li>
              <code className="font-mono text-xs bg-slate-100 px-1 py-0.5 rounded">
                src/data/mock-knot.json
              </code>
              {' — '}synthetic KnotData: 4 entity strands, ~18 beads, 6 crossings. Date range
              2024-01 – 2024-06.
            </li>
          </ul>
          <p className="mt-3 text-xs text-slate-400">
            All names and events are fictional. No data from real benchmark datasets is included.
          </p>
        </section>
      </main>
    </div>
  )
}
