
import { useEffect, useRef, useState } from 'react';
import {
  Send,
  Plus,
  Trash2,
  Bot,
  User,
  Info,
} from 'lucide-react';

import { useAppData } from '../context/AppDataContext';
import { answer, SUGGESTED_PROMPTS } from '../services/chatService';
import { apiClient, isMockMode } from '../api/apiClient';
import { formatDateTime } from '../utils/formatters';
import Button from '../components/common/Button';

// ---------------------------------------------------------
// WELCOME MESSAGE
// ---------------------------------------------------------

const WELCOME = {
  id: 'welcome',
  role: 'assistant',
  at: new Date().toISOString(),
  text: isMockMode
    ? 'Hi! I am your Product Assistant running in demo mode. I can answer using the sample workspace data.'
    : 'Hi! I am your AI Product Assistant. I can help generate PRDs, create user stories with acceptance criteria, prioritize features, and analyze product feedback.',
};

// ---------------------------------------------------------
// HELPERS
// ---------------------------------------------------------

const getArray = (...values) => {
  return values.find(Array.isArray) || [];
};

const getLatestArtifacts = (messages) => {
  const artifacts = {
    prd: null,
    user_stories: null,
    feature_prioritization: null,
  };

  messages.forEach((message) => {
    if (!message.artifact || !message.artifactType) {
      return;
    }

    const type = message.artifactType.toLowerCase();

    if (type.includes('prd')) {
      artifacts.prd = message.artifact;
    }

    if (type.includes('user_story') || type.includes('user-stor')) {
      artifacts.user_stories = message.artifact;
    }

    if (type.includes('priorit')) {
      artifacts.feature_prioritization = message.artifact;
    }
  });

  return artifacts;
};

// ---------------------------------------------------------
// COMPONENT
// ---------------------------------------------------------

export default function Chat() {
  const { raw, derived, analysis, refresh } = useAppData();

  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState('');

  const bottomRef = useRef(null);
  const conversationIdRef = useRef(
    `conversation-${Date.now()}`
  );
  // -------------------------------------------------------
  // RESTORE SAVED CONVERSATION
  // -------------------------------------------------------

  useEffect(() => {
    let active = true;

    const restoreHistory = async () => {
      try {
        const response = await apiClient.chat.getHistory();

        if (!active || !response?.success) {
          return;
        }

        // Support the possible response formats from the API.
        const savedMessages = Array.isArray(response.data)
          ? response.data
          : Array.isArray(response.data?.messages)
            ? response.data.messages
            : Array.isArray(response.data?.items)
              ? response.data.items
              : [];

        if (savedMessages.length > 0) {
          setMessages([
            WELCOME,
            ...savedMessages,
          ]);
        }
      } catch (err) {
        console.error(
          'Could not restore chat history:',
          err
        );
      }
    };

    restoreHistory();

    return () => {
      active = false;
    };
  }, []);
  // -------------------------------------------------------
  // AUTO SCROLL
  // -------------------------------------------------------

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
  }, [messages, thinking]);

  // -------------------------------------------------------
  // SAVE CHAT HISTORY
  // -------------------------------------------------------

  const persist = async (nextMessages) => {
    const saveable = nextMessages.filter(
      (message) => message.id !== 'welcome'
    );

    const response = await apiClient.chat.saveHistory(
      saveable
    );

    if (response && response.success === false) {
      console.error(
        'Could not save chat history:',
        response.message
      );
    }
  };

  // ---------------------------------------------------------
// BUILD AI REQUEST
// ---------------------------------------------------------

const getAnalysisList = (result, possibleKeys = []) => {
  if (Array.isArray(result)) {
    return result;
  }

  if (!result || typeof result !== 'object') {
    return [];
  }

  for (const key of possibleKeys) {
    if (Array.isArray(result[key])) {
      return result[key];
    }
  }

  return [];
};

const buildAIRequest = (message, conversationMessages) => {
  // Preserve artifacts generated earlier in this conversation.
  const generatedArtifacts = getLatestArtifacts(
    conversationMessages
  );

  // Original workspace feedback.
  const feedback = getArray(raw?.feedback);

  // Latest saved four-agent analysis.
  const latestResults = analysis?.latest?.results || {};

  // Agent 1: Theme Extraction.
  const themes = getAnalysisList(
    latestResults.themes,
    ['themes']
  );

  // Agent 2: Pain Point Identification.
  const painPoints = getAnalysisList(
    latestResults.pain_points,
    ['pain_points', 'painPoints']
  );

  // Agent 3: Feature Clustering.
  const featureClusters = getAnalysisList(
    latestResults.feature_clusters,
    ['clusters', 'feature_clusters', 'featureClusters']
  );

  // Agent 4: Trend Analysis.
  const trends = getAnalysisList(
    latestResults.trends,
    ['trends', 'trend_analysis', 'trendAnalysis']
  );

  return {
    conversation_id: conversationIdRef.current,

    product_name:
      raw?.workspace?.name ||
      raw?.product?.name ||
      raw?.workspaceName ||
      'Product',

    product_context:
      raw?.workspace?.description ||
      raw?.product?.description ||
      raw?.description ||
      '',

    message,

    intent: 'auto',

    conversation_history: conversationMessages
      .filter((item) => item.id !== 'welcome')
      .map((item) => ({
        role: item.role,
        content: item.text,
      })),

    analysis_context: {
      feedback,
      themes,
      pain_points: painPoints,
      feature_clusters: featureClusters,
      trends,
    },

    generated_artifacts: generatedArtifacts,
  };
};
  // -------------------------------------------------------
  // SEND MESSAGE
  // -------------------------------------------------------

  const send = async (text) => {
    const trimmed = (text ?? input).trim();

    if (!trimmed || thinking) {
      if (!trimmed) {
        setError('Please type a message before sending.');
      }
      return;
    }

    setError('');
    setInput('');

    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: trimmed,
      at: new Date().toISOString(),
    };

    const withUser = [...messages, userMsg];

    setMessages(withUser);
    setThinking(true);

    try {
      let reply;

      // ---------------------------------------------------
      // MOCK MODE
      // ---------------------------------------------------

      if (isMockMode) {
        await new Promise((resolve) =>
          setTimeout(resolve, 600)
        );

        reply = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: answer(trimmed, raw),
          at: new Date().toISOString(),
        };
      }

      // ---------------------------------------------------
      // LIVE AI MODE
      // ---------------------------------------------------

      else {
        const payload = buildAIRequest(
          trimmed,
          withUser
        );

        const response = await apiClient.chat.sendMessage(
          payload
        );

        if (!response?.success || !response?.data) {
          throw new Error(
            response?.message ||
            'The AI assistant could not process your request.'
          );
        }

        const aiData = response.data;

        const assistantText =
          aiData.assistant_message ||
          aiData.assistantMessage ||
          'The AI assistant returned an empty response.';

        reply = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: assistantText,
          at:
            aiData.generated_at ||
            new Date().toISOString(),

          // Preserve generated artifacts for later turns.
          artifactType: aiData.artifact_type || null,
          artifact: aiData.artifact || null,

          agentUsed: aiData.agent_used || null,
          intent: aiData.intent || null,
        };
      }

      const finalMessages = [...withUser, reply];

      setMessages(finalMessages);

      await persist(finalMessages);

    } catch (err) {
      console.error('Chat request failed:', err);

      setError(
        err.message ||
        'Something went wrong while contacting the AI assistant.'
      );

      // Preserve the user's message even if AI generation fails.
      await persist(withUser);

    } finally {
      setThinking(false);
    }
  };

  // -------------------------------------------------------
  // KEYBOARD HANDLER
  // -------------------------------------------------------

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  // -------------------------------------------------------
  // NEW CONVERSATION
  // -------------------------------------------------------

  const newConversation = async () => {
    if (thinking) return;

    setMessages([WELCOME]);
    setInput('');
    setError('');

    conversationIdRef.current =
      `conversation-${Date.now()}`;

    await apiClient.chat.clear();
    await refresh();
  };

  // -------------------------------------------------------
  // UI
  // -------------------------------------------------------

  return (
    <div className="grid h-[calc(100vh-10rem)] gap-4 lg:grid-cols-[260px_1fr]">

      {/* SIDEBAR */}

      <aside className="card hidden flex-col gap-4 overflow-hidden p-4 lg:flex">

        <Button
          onClick={newConversation}
          variant="outline"
          className="w-full"
          disabled={thinking}
        >
          <Plus size={16} />
          New conversation
        </Button>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-navy-500">
            Suggested prompts
          </p>

          <ul className="space-y-1.5">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <li key={prompt}>
                <button
                  onClick={() => send(prompt)}
                  disabled={thinking}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-xs transition hover:border-accent hover:bg-indigo-50 disabled:opacity-50 dark:border-navy-700 dark:hover:bg-indigo-500/10"
                >
                  {prompt}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-auto flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-xs text-navy-500 dark:bg-navy-900/40">
          <Info
            size={14}
            className="mt-0.5 shrink-0"
          />

          {isMockMode
            ? 'Demo mode: responses use local workspace data.'
            : 'AI mode: powered by your unified Product Assistant and specialized AI agents.'}
        </div>

      </aside>

      {/* CONVERSATION */}

      <section className="card flex min-h-0 flex-col overflow-hidden">

        {/* HEADER */}

        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-navy-700">

          <div>
            <p className="text-sm font-semibold">
              Product Copilot
            </p>

            <p className="text-xs text-navy-500">
              {isMockMode ? 'Demo / Mock Mode' : 'AI Powered Mode'}
              {' · '}
              {Math.max(0, messages.length - 1)} message(s)
            </p>
          </div>

          <div className="flex gap-1">

            <button
              onClick={newConversation}
              className="btn-ghost p-2 lg:hidden"
              aria-label="New conversation"
              disabled={thinking}
            >
              <Plus size={16} />
            </button>

            <button
              onClick={newConversation}
              className="btn-ghost p-2"
              aria-label="Clear conversation"
              disabled={thinking}
            >
              <Trash2 size={16} />
            </button>

          </div>
        </div>

        {/* MESSAGE LIST */}

        <div
          className="flex-1 space-y-4 overflow-y-auto p-5"
          aria-live="polite"
        >

          {messages.map((message) => (

            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === 'user'
                  ? 'flex-row-reverse'
                  : ''
              }`}
            >

              <div
                className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${
                  message.role === 'user'
                    ? 'bg-accent text-white'
                    : 'bg-indigo-100 text-accent-600 dark:bg-indigo-500/20'
                }`}
              >
                {message.role === 'user'
                  ? <User size={15} />
                  : <Bot size={15} />}
              </div>

              <div
                className={`max-w-[80%] ${
                  message.role === 'user'
                    ? 'text-right'
                    : ''
                }`}
              >

                <div
                  className={`inline-block whitespace-pre-line rounded-2xl px-4 py-2.5 text-left text-sm leading-relaxed ${
                    message.role === 'user'
                      ? 'rounded-tr-sm bg-accent text-white'
                      : 'rounded-tl-sm bg-slate-100 text-navy-800 dark:bg-navy-700 dark:text-slate-100'
                  }`}
                >
                  {message.text}
                </div>

                {/* AGENT INFORMATION */}

                {message.agentUsed && (
                  <p className="mt-1 text-[11px] text-accent-600">
                    Agent: {message.agentUsed.replaceAll('_', ' ')}
                  </p>
                )}

                {/* GENERATED ARTIFACT INDICATOR */}

                {message.artifactType && (
                  <p className="mt-1 text-[11px] font-medium text-emerald-600">
                    Generated: {message.artifactType.replaceAll('_', ' ')}
                  </p>
                )}

                <p className="mt-1 text-[11px] text-navy-500">
                  {formatDateTime(message.at)}
                </p>

              </div>
            </div>

          ))}

          {/* THINKING INDICATOR */}

          {thinking && (
            <div className="flex gap-3">

              <div className="grid h-8 w-8 place-items-center rounded-full bg-indigo-100 text-accent-600 dark:bg-indigo-500/20">
                <Bot size={15} />
              </div>

              <div
                className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3 dark:bg-navy-700"
                aria-label="Assistant is thinking"
              >
                <span className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 animate-bounce rounded-full bg-navy-500"
                      style={{
                        animationDelay: `${i * 0.15}s`,
                      }}
                    />
                  ))}
                </span>
              </div>

            </div>
          )}

          <div ref={bottomRef} />

        </div>

        {/* MOBILE SUGGESTIONS */}

        <div className="flex gap-2 overflow-x-auto border-t border-slate-200 px-4 pt-3 lg:hidden dark:border-navy-700">

          {SUGGESTED_PROMPTS.slice(0, 4).map((prompt) => (
            <button
              key={prompt}
              onClick={() => send(prompt)}
              disabled={thinking}
              className="shrink-0 rounded-full border border-slate-300 px-3 py-1 text-xs hover:border-accent disabled:opacity-50 dark:border-navy-700"
            >
              {prompt}
            </button>
          ))}

        </div>

        {/* MESSAGE INPUT */}

        <div className="border-t border-slate-200 p-4 dark:border-navy-700">

          {error && (
            <p
              role="alert"
              className="mb-2 text-xs text-rose-600"
            >
              {error}
            </p>
          )}

          <div className="flex items-end gap-2">

            <textarea
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                setError('');
              }}
              onKeyDown={onKeyDown}
              rows={2}
              placeholder="Ask about feedback, generate a PRD, create user stories, or prioritize features..."
              className="input min-h-[44px] resize-none"
              aria-label="Message"
              disabled={thinking}
            />

            <Button
              onClick={() => send()}
              disabled={thinking || !input.trim()}
              className="h-[44px]"
            >
              <Send size={16} />
              Send
            </Button>

          </div>
        </div>

      </section>
    </div>
  );
}
