import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AiContext, AiSettings, Trade } from '../api/types';
import { wrap } from '../test/helpers';
import AiSettingsSection from './AiSettingsSection';
import TradeContextDialog from './TradeContextDialog';

const KEY = 'sk-test-FULLKEY-0123456789-abcd';

const ai = (over: Partial<AiContext> = {}): AiContext => ({
  headline: 'Headline text', summary: 'Summary text', signals: [{ type: 'trade_size_anomaly', explanation: 'size words' }], limitations: 'Limits.',
  generated_for: 'flagged', provider: 'openai', model: 'gpt-4o-mini', prompt_version: '3', generated_at: '2026-10-12T09:30:00', ...over,
});

function trade(over: { flagged?: boolean; ai?: AiContext | null } = {}): Trade {
  return {
    id: 7, politician_name: 'A B', ticker: 'BA', transaction_type: 'buy', transaction_date: '2026-02-20',
    context: { evidence: [], flagged_for_contextual_review: over.flagged ?? true, ai_context: over.ai ?? null, committee_relevance: null, excess_horizon_days: 90, notice: 'n' },
  } as unknown as Trade;
}

/** An in-memory stand-in for the desktop AI routes. Like the real ones it never returns a stored key, only the masked tail. */
function fakeAi(opts: { desktop?: boolean; configured?: string[]; provider?: string } = {}) {
  const st = {
    desktop: opts.desktop ?? true, provider: opts.provider ?? 'openai', models: {} as Record<string, string>, keys: new Set(opts.configured ?? []),
    calls: [] as string[], bodies: [] as unknown[], generate: null as null | (() => Promise<Response>), testOk: true,
    bulk: { to_generate: 3, already_cached: 1, flagged_total: 4 }, bulkStatus: { state: 'idle' } as Record<string, unknown>,
  };
  const meta = [
    { id: 'openai', label: 'OpenAI', default_model: 'gpt-4o-mini', suggested_models: ['gpt-4o-mini'] },
    { id: 'anthropic', label: 'Anthropic (Claude)', default_model: 'claude-haiku-5-5', suggested_models: ['claude-haiku-5-5'] },
  ];
  const settings = (): AiSettings => ({
    provider: st.provider, model: st.models[st.provider] ?? meta.find((m) => m.id === st.provider)!.default_model,
    providers: meta.map((m) => ({ ...m, configured: st.keys.has(m.id), masked: st.keys.has(m.id) ? 'sk-••••••••abcd' : null, model: st.models[m.id] ?? m.default_model })),
    configured: st.keys.has(st.provider), storage_error: null,
    notice: 'AI does not determine which trades POLTRACKER flags. It explains the deterministic context already calculated by POLTRACKER.',
    key_notice: 'Your API key is stored locally in the macOS Keychain and is sent only to the selected AI provider when you request an explanation.',
  });
  const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { 'Content-Type': 'application/json' } });
  const handler = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost');
    const path = url.pathname.replace(/^\/api/, '');
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    st.calls.push(`${method} ${path}`);
    st.bodies.push(body);
    if (!st.desktop && path.startsWith('/ai')) return json({ detail: 'Not Found' }, 404);
    if (path === '/ai/settings') return json(settings());
    if (path === '/ai/provider') {
      st.provider = body.provider;
      if ('model' in body) body.model ? (st.models[body.provider] = body.model) : delete st.models[body.provider];
      return json(settings());
    }
    if (path === '/ai/key' && method === 'POST') {
      st.keys.add(body.provider);
      return json(settings());
    }
    if (path === '/ai/key' && method === 'DELETE') {
      st.keys.delete(url.searchParams.get('provider')!);
      return json(settings());
    }
    if (path === '/ai/test') return json(st.testOk ? { ok: true, code: null, message: 'Connected to OpenAI.' } : { ok: false, code: 'invalid_key', message: 'OpenAI rejected the API key (HTTP 401).' });
    if (path === '/ai/generate-flagged/preview') return json({ provider: st.provider, provider_label: 'OpenAI', model: 'gpt-4o-mini', configured: true, estimated_api_calls: st.bulk.to_generate, ...st.bulk });
    if (path === '/ai/generate-flagged/status') return json(st.bulkStatus);
    if (path === '/ai/generate-flagged' && method === 'POST') {
      st.bulkStatus = { state: 'running', total: 3, done: 0, generated: 0, cached: 0, rejected: 0, errors: 0, message: null };
      return json(st.bulkStatus);
    }
    if (/^\/trades\/\d+\/ai-context\/generate$/.test(path)) return st.generate ? st.generate() : json({ ai_context: ai({ provider: st.provider }), from_cache: false });
    return json({ detail: 'unexpected ' + path }, 500);
  };
  return { st, handler };
}

let api: ReturnType<typeof fakeAi>;
function start(ui: React.ReactElement, opts: Parameters<typeof fakeAi>[0] = {}) {
  api = fakeAi(opts);
  vi.stubGlobal('fetch', vi.fn(api.handler));
  return render(wrap(ui, '/trades'));
}
const providerCalls = () => api.st.calls.filter((c) => c.includes('ai-context/generate'));

beforeEach(() => vi.unstubAllGlobals());

describe('AI settings', () => {
  it('shows the notices, the provider choice and an unconfigured status', async () => {
    start(<AiSettingsSection />);
    expect(await screen.findByText(/○ Not configured/)).toBeInTheDocument();
    expect(screen.getByText(/stored locally in the macOS Keychain and is sent only to the selected AI provider/)).toBeInTheDocument();
    expect(screen.getAllByText(/does not determine which trades POLTRACKER flags/).length).toBeGreaterThan(0);
    expect(screen.getByRole('combobox', { name: /provider/i })).toHaveTextContent('OpenAI');
    expect(screen.getByRole('button', { name: 'Test connection' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Remove key' })).toBeDisabled();
  });

  it('switches provider and remembers the choice', async () => {
    const user = userEvent.setup();
    start(<AiSettingsSection />);
    await user.click(await screen.findByRole('combobox', { name: /provider/i }));
    await user.click(await screen.findByRole('option', { name: /Anthropic/ }));
    await waitFor(() => expect(api.st.provider).toBe('anthropic'));
    expect(await screen.findByLabelText('Model')).toHaveValue('claude-haiku-5-5');
  });

  it('saves a key, then shows only the masked tail and clears the field', async () => {
    const user = userEvent.setup();
    start(<AiSettingsSection />);
    const field = await screen.findByLabelText('API key');
    expect(field).toHaveAttribute('type', 'password');
    await user.type(field, KEY);
    await user.click(screen.getByRole('button', { name: 'Save key' }));
    expect(await screen.findByText(/OpenAI key configured: sk-••••••••abcd/)).toBeInTheDocument();
    expect(screen.getByLabelText('API key')).toHaveValue('');
    expect(document.body.textContent).not.toContain(KEY);
    expect(await screen.findByRole('button', { name: 'Replace key' })).toBeInTheDocument(); // now a replace, not a first save
    expect(JSON.stringify(api.st.bodies.filter(Boolean))).toContain(KEY); // it was sent once, to save it...
    expect(api.st.calls.filter((c) => c === 'GET /ai/settings').length).toBeGreaterThan(0); // ...and nothing read it back
  });

  it('tests the connection and reports success and failure', async () => {
    const user = userEvent.setup();
    start(<AiSettingsSection />, { configured: ['openai'] });
    await user.click(await screen.findByRole('button', { name: 'Test connection' }));
    expect(await screen.findByText('Connected to OpenAI.')).toBeInTheDocument();
    expect(screen.getByText(/● Connected/)).toBeInTheDocument();
    api.st.testOk = false;
    await user.click(screen.getByRole('button', { name: 'Test connection' }));
    expect(await screen.findByText(/rejected the API key/)).toBeInTheDocument();
    expect(screen.queryByText(/● Connected/)).not.toBeInTheDocument();
  });

  it('removes a key only after confirmation', async () => {
    const user = userEvent.setup();
    start(<AiSettingsSection />, { configured: ['openai'] });
    await user.click(await screen.findByRole('button', { name: 'Remove key' }));
    expect(api.st.keys.has('openai')).toBe(true);
    const dlg = await screen.findByRole('dialog');
    await user.click(within(dlg).getByRole('button', { name: 'Remove key' }));
    await waitFor(() => expect(api.st.keys.has('openai')).toBe(false));
    expect(await screen.findByText(/○ Not configured/)).toBeInTheDocument();
  });

  it('is explained as desktop-only on the web build', async () => {
    start(<AiSettingsSection />, { desktop: false });
    expect(await screen.findByText(/available in the POLTRACKER desktop app/)).toBeInTheDocument();
  });

  it('bulk generation shows the count, provider and calls, and needs explicit confirmation', async () => {
    const user = userEvent.setup();
    start(<AiSettingsSection />, { configured: ['openai'] });
    await user.click(await screen.findByRole('button', { name: /Generate explanations for flagged trades…/ }));
    const dlg = await screen.findByRole('dialog');
    expect(await within(dlg).findByText(/needs? an explanation|need an explanation/)).toBeInTheDocument();
    expect(within(dlg).getByText('Provider: OpenAI')).toBeInTheDocument();
    expect(within(dlg).getByText('Estimated API calls: 3')).toBeInTheDocument();
    expect(api.st.calls).not.toContain('POST /ai/generate-flagged');
    await user.click(within(dlg).getByRole('button', { name: 'Confirm and generate' }));
    await waitFor(() => expect(api.st.calls).toContain('POST /ai/generate-flagged'));
    expect(await screen.findByText(/Generating explanations… 0 of 3/)).toBeInTheDocument();
  });
});

describe('Context dialog AI section', () => {
  it('does not call a provider just because the dialog opened, and offers to generate', async () => {
    start(<TradeContextDialog trade={trade()} onClose={() => {}} />, { configured: ['openai'] });
    expect(await screen.findByText('No AI explanation has been generated.')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Generate explanation' })).toBeEnabled();
    expect(providerCalls()).toEqual([]);
  });

  it('offers to configure a provider when there is no key, and opens the AI settings', async () => {
    const user = userEvent.setup();
    start(<TradeContextDialog trade={trade()} onClose={() => {}} />);
    const btn = await screen.findByRole('button', { name: 'Configure AI provider' });
    expect(screen.queryByRole('button', { name: 'Generate explanation' })).not.toBeInTheDocument();
    await user.click(btn);
    expect(providerCalls()).toEqual([]);
  });

  it('shows Generating…, blocks a second click, then shows the explanation with provider, model and time', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    let release!: () => void;
    start(<TradeContextDialog trade={trade()} onClose={() => {}} />, { configured: ['openai'] });
    api.st.generate = () => new Promise<Response>((res) => { release = () => res(new Response(JSON.stringify({ ai_context: ai(), from_cache: false }), { status: 200, headers: { 'Content-Type': 'application/json' } })); });
    await user.click(await screen.findByRole('button', { name: 'Generate explanation' }));
    const busy = await screen.findByRole('button', { name: 'Generating explanation…' });
    expect(busy).toBeDisabled();
    await user.click(busy);
    expect(providerCalls()).toHaveLength(1);
    release();
    expect(await screen.findByText('Headline text')).toBeInTheDocument();
    expect(screen.getByTestId('ai-meta')).toHaveTextContent('Provider: OpenAI · Model: gpt-4o-mini · Generated: 2026-10-12 09:30 UTC');
    expect(screen.getByRole('button', { name: 'Regenerate' })).toBeEnabled();
  });

  it('regenerate asks again with regenerate=true', async () => {
    const user = userEvent.setup();
    start(<TradeContextDialog trade={trade({ ai: ai() })} onClose={() => {}} />, { configured: ['openai'] });
    await user.click(await screen.findByRole('button', { name: 'Regenerate' }));
    await waitFor(() => expect(providerCalls()).toHaveLength(1));
    expect(api.st.bodies.at(-1)).toMatchObject({ regenerate: true });
  });

  it('keeps showing a cached explanation with no key, and offers to configure instead of regenerate', async () => {
    start(<TradeContextDialog trade={trade({ ai: ai({ provider: 'anthropic', model: 'claude-haiku-5-5' }) })} onClose={() => {}} />);
    expect(await screen.findByText('Summary text')).toBeInTheDocument();
    expect(screen.getByTestId('ai-meta')).toHaveTextContent('Provider: Claude (Anthropic) · Model: claude-haiku-5-5');
    expect(await screen.findByRole('button', { name: 'Configure AI provider' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Regenerate' })).not.toBeInTheDocument();
  });

  it('another provider\'s explanation is labelled as such and the button generates with the selected provider', async () => {
    const user = userEvent.setup();
    start(<TradeContextDialog trade={trade({ ai: ai() })} onClose={() => {}} />, { configured: ['openai', 'anthropic'], provider: 'anthropic' });
    const btn = await screen.findByRole('button', { name: 'Generate with Anthropic (Claude)' });
    expect(screen.getByTestId('ai-meta')).toHaveTextContent('Provider: OpenAI');
    await user.click(btn);
    await waitFor(() => expect(providerCalls()).toHaveLength(1));
    expect(api.st.bodies.at(-1)).toMatchObject({ regenerate: false });
  });

  it('shows a clean error and no raw output when generation is rejected', async () => {
    const user = userEvent.setup();
    start(<TradeContextDialog trade={trade()} onClose={() => {}} />, { configured: ['openai'] });
    api.st.generate = async () => new Response(JSON.stringify({ detail: { code: 'validation_rejected', message: 'AI explanation could not be generated from the available evidence.' } }), { status: 422, headers: { 'Content-Type': 'application/json' } });
    await user.click(await screen.findByRole('button', { name: 'Generate explanation' }));
    expect(await screen.findByText('AI explanation could not be generated from the available evidence.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Generate explanation' })).toBeEnabled();
  });

  it('an unflagged trade gets no default generate button; the advanced action is labelled manual and does not claim a flag', async () => {
    const user = userEvent.setup();
    start(<TradeContextDialog trade={trade({ flagged: false })} onClose={() => {}} />, { configured: ['openai'] });
    expect(await screen.findByRole('button', { name: 'Generate manual explanation' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Generate explanation' })).not.toBeInTheDocument();
    api.st.generate = async () => new Response(JSON.stringify({ ai_context: ai({ generated_for: 'manual' }), from_cache: false }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    await user.click(screen.getByRole('button', { name: 'Generate manual explanation' }));
    expect(await screen.findByText(/Manual context explanation — this trade is not flagged by the default POLTRACKER methodology\./)).toBeInTheDocument();
    expect(api.st.bodies.at(-1)).toMatchObject({ manual: true });
  });

  it('on the web build it says generation is desktop-only and never offers it', async () => {
    start(<TradeContextDialog trade={trade()} onClose={() => {}} />, { desktop: false });
    expect(await screen.findByText(/available in the POLTRACKER desktop app/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Generate explanation' })).not.toBeInTheDocument();
  });
});
