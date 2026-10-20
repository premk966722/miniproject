import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  FileText,
  Loader2,
  MessageSquareText,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api';
import type { ChatResponse, Citation, EvidenceItem, SourceRecord } from './types';

const sampleQuestion = 'What should I verify before deciding between the old and new tax regime?';

const statusStyles: Record<string, string> = {
  answered: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  'needs_clarification': 'bg-amber-100 text-amber-800 border-amber-200',
  insufficient_evidence: 'bg-rose-100 text-rose-800 border-rose-200',
  conflicting_evidence: 'bg-violet-100 text-violet-800 border-violet-200',
  generation_error: 'bg-red-100 text-red-800 border-red-200',
};

function App() {
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [question, setQuestion] = useState(sampleQuestion);
  const [taxYear, setTaxYear] = useState('');
  const [regime, setRegime] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const questionInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    void loadSources();
  }, []);

  const loadSources = async () => {
    try {
      const data = await api.getSources();
      setSources(data.sources || []);
    } catch {
      setSources([]);
    }
  };

  const normalizeResponse = (payload: ChatResponse): ChatResponse => {
    const answerText = payload.answer_text || payload.answer || 'No answer was returned by the backend.';
    const citations = (payload.citations || []).map((citation) => ({
      ...citation,
      document_title: citation.document_title || citation.title || 'Untitled document',
      issuing_authority: citation.issuing_authority || citation.authority || 'Unknown authority',
      section_identifier: citation.section_identifier || citation.section || 'General guidance',
      supporting_passage: citation.supporting_passage || citation.passage || '',
      url: citation.url || '',
    }));

    return {
      ...payload,
      answer: answerText,
      answer_text: answerText,
      citations,
      status: payload.status || 'answered',
      tax_period: payload.tax_period === undefined ? null : payload.tax_period,
      evidence_sufficient: payload.evidence_sufficient ?? false,
      clarification_question: payload.clarification_question || undefined,
      limitations: payload.limitations || [],
      supporting_evidence: payload.supporting_evidence || [],
    };
  };

  const askQuestion = async (customQuestion?: string) => {
    const submission = (customQuestion ?? question).trim();
    if (!submission || loading) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        question: submission,
        tax_year: taxYear || undefined,
        regime: regime || undefined,
        conversation_id: conversationId,
      };
      const result = await api.postChat(payload);
      const normalized = normalizeResponse(result);
      setResponse(normalized);
      setConversationId(normalized.conversation_id || conversationId);
      if (!conversationId && normalized.conversation_id) {
        setConversationId(normalized.conversation_id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'The backend request failed.';
      setError(message);
      setResponse({
        answer: 'The system could not complete the request. Please retry or start the backend service.',
        citations: [],
        status: 'generation_error',
        evidence_sufficient: false,
        clarification_question: undefined,
      });
    } finally {
      setLoading(false);
    }
  };

  const focusQuestionInput = () => {
    questionInputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    questionInputRef.current?.focus({ preventScroll: true });
  };

  const statusTone = useMemo(() => {
    const status = response?.status || 'answered';
    return statusStyles[status] || statusStyles.answered;
  }, [response]);

  const renderStatus = (status?: string) => {
    const normalized = status || 'answered';
    return (
      <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${statusStyles[normalized] || statusStyles.answered}`}>
        {normalized === 'answered' ? <CheckCircle2 className="h-3.5 w-3.5" /> : normalized === 'needs_clarification' ? <AlertTriangle className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
        {normalized.replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white shadow-sm">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-bold tracking-tight text-slate-900">TAX-SHIELD</div>
              <div className="text-[11px] uppercase tracking-[0.1em] text-slate-500">Evidence-grounded tax research</div>
            </div>
          </div>

          <nav className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
            <a href="#features" className="transition hover:text-slate-900">Features</a>
            <a href="#workflow" className="transition hover:text-slate-900">How it works</a>
            <a href="#sources" className="transition hover:text-slate-900">Sources</a>
            <a href="#methodology" className="transition hover:text-slate-900">Methodology</a>
          </nav>

          <button
            onClick={() => {
              setConversationId(undefined);
              setResponse(null);
              setQuestion(sampleQuestion);
            }}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
          >
            <Plus className="h-4 w-4" />
            New question
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <section className="grid gap-10 py-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">
              <Sparkles className="h-3.5 w-3.5" />
              Official-source aware research
            </div>
            <h1 className="max-w-xl text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">
              Indian Tax Answers. <span className="text-blue-700">Grounded in Evidence.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
              Understand Indian income tax provisions through hybrid AI retrieval, official legal sources, and transparent evidence-backed explanations.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <button
                onClick={focusQuestionInput}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-700 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800"
              >
                Ask a Tax Question
                <ArrowRight className="h-4 w-4" />
              </button>
              <a
                href="#workflow"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400"
              >
                Explore how it works
              </a>
            </div>

            <div className="mt-10 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <p className="font-semibold text-slate-800">Illustrative answer preview</p>
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700">
                  Evidence-aware
                </span>
              </div>
              <p className="text-sm leading-7 text-slate-600">
                The final answer depends on the tax period, the taxpayer profile, and whether the question concerns a transition or a current provision. Official-source guidance should always be checked before relying on a legal conclusion.
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
                <span className="rounded-full bg-slate-100 px-2 py-1">Official tax sources</span>
                <span className="rounded-full bg-slate-100 px-2 py-1">Tax-year awareness</span>
                <span className="rounded-full bg-slate-100 px-2 py-1">Traceable citations</span>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm ring-1 ring-slate-100">
            <div className="mb-4 flex items-center justify-between">
              <p className="font-semibold text-slate-800">Tax research workspace</p>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                {taxYear || 'Period not selected'}
              </span>
            </div>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-600">Question</span>
              <textarea
                ref={questionInputRef}
                id="tax-question"
                rows={5}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about a deduction, filing year, regime, or section-specific issue..."
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white"
              />
            </label>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-600">Tax period</span>
                <select
                  value={taxYear}
                  onChange={(event) => setTaxYear(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white"
                >
                  <option value="">No specific period</option>
                  <option value="2024-25">2024-25</option>
                  <option value="2025-26">2025-26</option>
                  <option value="2023-24">2023-24</option>
                </select>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-600">Regime</span>
                <select
                  value={regime}
                  onChange={(event) => setRegime(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white"
                >
                  <option value="">Not specified</option>
                  <option value="old">Old</option>
                  <option value="new">New</option>
                </select>
              </label>
            </div>

            <div className="mt-4 flex gap-3">
              <button
                onClick={() => askQuestion()}
                disabled={loading}
                className="flex-1 rounded-xl bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <span className="inline-flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Checking evidence...
                  </span>
                ) : (
                  'Search legal sources'
                )}
              </button>
              <button
                onClick={() => setQuestion('')}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-600 transition hover:border-slate-300"
              >
                Clear
              </button>
            </div>

            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              {error ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 font-medium text-red-700">
                    <AlertTriangle className="h-4 w-4" />
                    Request failed
                  </div>
                  <p>{error}</p>
                  <button
                    onClick={() => askQuestion()}
                    className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 text-xs font-medium text-red-700 transition hover:bg-red-50"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Retry
                  </button>
                </div>
              ) : response ? (
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="mb-2 text-xs uppercase tracking-[0.12em] text-slate-500">Result</div>
                      {renderStatus(response.status)}
                    </div>
                    {response.tax_period ? (
                      <span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-600">
                        {response.tax_period}
                      </span>
                    ) : null}
                  </div>
                  <p className="leading-7 text-slate-700">{response.answer}</p>

                  {response.clarification_question ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
                      <div className="mb-1 font-semibold">Clarification needed</div>
                      <p>{response.clarification_question}</p>
                    </div>
                  ) : null}

                  {response.limitations && response.limitations.length > 0 ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                      <div className="mb-1 font-semibold">Limitations</div>
                      <ul className="list-disc space-y-1 pl-4">
                        {response.limitations.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {response.citations && response.citations.length > 0 ? (
                    <ul className="space-y-2 text-xs text-slate-600">
                      {response.citations.map((citation, index) => (
                        <li key={`${citation.citation_id || citation.url || index}`} className="rounded-xl border border-slate-200 bg-white p-3">
                          <div className="flex items-center justify-between gap-2">
                            <div className="font-medium text-slate-800">{citation.document_title || citation.title || 'Untitled source'}</div>
                            {citation.url ? (
                              <a href={citation.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-blue-700">
                                Open <ExternalLink className="h-3.5 w-3.5" />
                              </a>
                            ) : null}
                          </div>
                          <div className="mt-1 text-slate-500">{citation.issuing_authority || citation.authority || 'Unknown authority'} · {citation.section_identifier || citation.section || 'General guidance'}</div>
                          <div className="mt-2 text-slate-600">{citation.supporting_passage || citation.passage || 'No passage available.'}</div>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p>Official-source guidance will appear here after retrieval.</p>
              )}
            </div>
          </div>
        </section>

        <section id="features" className="mt-20">
          <div className="mb-8 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">System capabilities</p>
            <h2 className="mt-2 text-3xl font-bold text-slate-900">Built for legal research clarity.</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {[
              { icon: Search, title: 'Hybrid retrieval prototype', text: 'BM25 and a deterministic vector-style placeholder are combined with reciprocal-rank fusion; semantic embeddings are not configured.' },
              { icon: BookOpen, title: 'Tax-year aware', text: 'Results are filtered by the stated tax or assessment year when the question is period-specific.' },
              { icon: Building2, title: 'Official-source traceability', text: 'The system preserves document provenance and points back to the original legal source.' },
              { icon: CheckCircle2, title: 'Evidence validation', text: 'The app checks sufficiency, applicability, and conflict signals before presenting conclusions.' },
            ].map(({ icon: Icon, title, text }) => (
              <div key={title} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-blue-700">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="workflow" className="mt-20 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-8 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">How it works</p>
            <h2 className="mt-2 text-3xl font-bold text-slate-900">From question to grounded answer</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {[
              'Ask a question and specify the relevant tax period when needed.',
              'Retrieve candidate passages and validate source provenance and legal applicability.',
              'Return a bounded response with citations, limitations, and a clarification or abstention when evidence is insufficient.',
            ].map((step, index) => (
              <div key={step} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">{index + 1}</div>
                <p className="text-base font-medium text-slate-800">{step}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="sources" className="mt-20 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">Source coverage</p>
              <h2 className="mt-2 text-3xl font-bold text-slate-900">Official-source ingestion</h2>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700">
              <Building2 className="h-4 w-4" />
              {sources.length} registered source{sources.length === 1 ? '' : 's'}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {sources.length > 0 ? (
              sources.map((source) => (
                <div key={source.source_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-slate-800">{source.issuing_authority}</p>
                    <span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-600">
                      {source.ingestion_status}
                    </span>
                  </div>
                  <a href={source.source_url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-sm text-blue-700 hover:text-blue-800">
                    {source.source_url}
                  </a>
                  <p className="mt-2 text-xs text-slate-500">{source.document_type} · {source.source_category}</p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                No official sources have been loaded yet. Start the FastAPI backend to populate the source registry.
              </div>
            )}
          </div>
        </section>

        <section id="methodology" className="mt-20 pb-8">
          <div className="rounded-3xl border border-slate-200 bg-slate-900 p-8 text-white shadow-sm">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-slate-200">
              <FileText className="h-3.5 w-3.5" />
              Methodology
            </div>
            <h2 className="text-3xl font-bold">Retrieval, validation, and grounded generation</h2>
            <div className="mt-5 grid gap-5 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-700 bg-slate-800 p-4">
                <div className="mb-2 font-semibold text-slate-100">Hybrid retrieval</div>
                <p className="text-sm leading-6 text-slate-300">The prototype combines BM25 with a deterministic vector-style placeholder using reciprocal-rank fusion; it does not use trained semantic embeddings.</p>
              </div>
              <div className="rounded-2xl border border-slate-700 bg-slate-800 p-4">
                <div className="mb-2 font-semibold text-slate-100">Evidence validation</div>
                <p className="text-sm leading-6 text-slate-300">Source authority, period applicability, and metadata completeness are checked before the answer is considered supported.</p>
              </div>
              <div className="rounded-2xl border border-slate-700 bg-slate-800 p-4">
                <div className="mb-2 font-semibold text-slate-100">Citations and uncertainty</div>
                <p className="text-sm leading-6 text-slate-300">The final answer includes traced citations and is designed to abstain or request clarification when the evidence is insufficient.</p>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
