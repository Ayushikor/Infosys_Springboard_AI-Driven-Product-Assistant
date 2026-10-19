import { useEffect, useRef, useState } from 'react';
import { Send, Plus, Trash2, Bot, User, Info } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { answer, SUGGESTED_PROMPTS } from '../services/chatService';
import { apiClient } from '../api/apiClient';
import { formatDateTime } from '../utils/formatters';
import Button from '../components/common/Button';

const WELCOME = {
  id: 'welcome', role: 'assistant', at: new Date().toISOString(),
  text: 'Hi, I am the Copilot in demo/mock mode. I answer using your current feedback, themes, features, and roadmap. No external AI is used.',
};

export default function Chat() {
  const { raw, derived, refresh } = useAppData();
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);

  // Restore saved conversation once data is available.
  useEffect(() => {
    if (raw?.chat?.length) setMessages(raw.chat);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [raw?.chat?.length]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, thinking]);

  const persist = async (next) => {
    const saveable = next.filter((m) => m.id !== 'welcome');
    await apiClient.chat.saveHistory(saveable);
  };

  const send = async (text) => {
    const trimmed = (text ?? input).trim();
    if (!trimmed) { setError('Please type a message before sending.'); return; }
    setError('');
    setInput('');
    const userMsg = { id: `u-${Date.now()}`, role: 'user', text: trimmed, at: new Date().toISOString() };
    const withUser = [...messages, userMsg];
    setMessages(withUser);
    setThinking(true);
    // Short artificial delay so the typing indicator is visible; the reply itself is local.
    await new Promise((r) => setTimeout(r, 600));
    const reply = { id: `a-${Date.now()}`, role: 'assistant', text: answer(trimmed, raw), at: new Date().toISOString() };
    const final = [...withUser, reply];
    setMessages(final);
    setThinking(false);
    await persist(final);
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const newConversation = async () => {
    setMessages([WELCOME]);
    await apiClient.chat.clear();
    await refresh();
  };

  return (
    <div className="grid h-[calc(100vh-10rem)] gap-4 lg:grid-cols-[260px_1fr]">
      {/* Sidebar: suggestions and history */}
      <aside className="card hidden flex-col gap-4 overflow-hidden p-4 lg:flex">
        <Button onClick={newConversation} variant="outline" className="w-full"><Plus size={16} />New conversation</Button>
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-navy-500">Suggested prompts</p>
          <ul className="space-y-1.5">
            {SUGGESTED_PROMPTS.map((p) => (
              <li key={p}>
                <button onClick={() => send(p)} className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-xs transition hover:border-accent hover:bg-indigo-50 dark:border-navy-700 dark:hover:bg-indigo-500/10">{p}</button>
              </li>
            ))}
          </ul>
        </div>
        <div className="mt-auto flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-xs text-navy-500 dark:bg-navy-900/40">
          <Info size={14} className="mt-0.5 shrink-0" />Rule-based, local responses. Answers reflect the data currently in your workspace.
        </div>
      </aside>

      {/* Conversation */}
      <section className="card flex min-h-0 flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-navy-700">
          <div>
            <p className="text-sm font-semibold">Copilot</p>
            <p className="text-xs text-navy-500">Demo / mock mode · {messages.length - 1} message(s)</p>
          </div>
          <div className="flex gap-1">
            <button onClick={newConversation} className="btn-ghost p-2 lg:hidden" aria-label="New conversation"><Plus size={16} /></button>
            <button onClick={newConversation} className="btn-ghost p-2" aria-label="Clear conversation"><Trash2 size={16} /></button>
          </div>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5" aria-live="polite">
          {messages.map((m) => (
            <div key={m.id} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${m.role === 'user' ? 'bg-accent text-white' : 'bg-indigo-100 text-accent-600 dark:bg-indigo-500/20'}`}>
                {m.role === 'user' ? <User size={15} /> : <Bot size={15} />}
              </div>
              <div className={`max-w-[80%] ${m.role === 'user' ? 'text-right' : ''}`}>
                <div className={`inline-block whitespace-pre-line rounded-2xl px-4 py-2.5 text-left text-sm leading-relaxed ${m.role === 'user' ? 'rounded-tr-sm bg-accent text-white' : 'rounded-tl-sm bg-slate-100 text-navy-800 dark:bg-navy-700 dark:text-slate-100'}`}>
                  {m.text}
                </div>
                <p className="mt-1 text-[11px] text-navy-500">{formatDateTime(m.at)}</p>
              </div>
            </div>
          ))}
          {thinking && (
            <div className="flex gap-3">
              <div className="grid h-8 w-8 place-items-center rounded-full bg-indigo-100 text-accent-600 dark:bg-indigo-500/20"><Bot size={15} /></div>
              <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3 dark:bg-navy-700" aria-label="Assistant is typing">
                <span className="flex gap-1">{[0, 1, 2].map((i) => <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-navy-500" style={{ animationDelay: `${i * 0.15}s` }} />)}</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Mobile suggestions */}
        <div className="flex gap-2 overflow-x-auto border-t border-slate-200 px-4 pt-3 lg:hidden dark:border-navy-700">
          {SUGGESTED_PROMPTS.slice(0, 4).map((p) => (
            <button key={p} onClick={() => send(p)} className="shrink-0 rounded-full border border-slate-300 px-3 py-1 text-xs hover:border-accent dark:border-navy-700">{p}</button>
          ))}
        </div>

        <div className="border-t border-slate-200 p-4 dark:border-navy-700">
          {error && <p role="alert" className="mb-2 text-xs text-rose-600">{error}</p>}
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => { setInput(e.target.value); setError(''); }}
              onKeyDown={onKeyDown}
              rows={2}
              placeholder="Ask about feedback, themes, RICE, roadmap, or request a PRD… (Enter to send, Shift+Enter for a new line)"
              className="input min-h-[44px] resize-none"
              aria-label="Message"
            />
            <Button onClick={() => send()} disabled={thinking} className="h-[44px]"><Send size={16} />Send</Button>
          </div>
        </div>
      </section>
    </div>
  );
}
