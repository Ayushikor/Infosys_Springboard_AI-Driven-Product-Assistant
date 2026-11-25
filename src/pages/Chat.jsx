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

const unwrapArtifact = (artifact) => {

  if (!artifact || typeof artifact !== 'object') return artifact;

  // Support common API wrappers without changing the actual PRD payload.

  if (artifact.artifact && typeof artifact.artifact === 'object') {

    return artifact.artifact;

  }

  if (

    artifact.data &&

    typeof artifact.data === 'object' &&

    !Array.isArray(artifact.data)

  ) {

    const data = artifact.data;

    if (

      data.functional_requirements ||

      data.requirements ||

      data.problem_statement ||

      data.prd

    ) {

      return data.prd && typeof data.prd === 'object' ? data.prd : data;

    }

  }

  if (artifact.prd && typeof artifact.prd === 'object') {

    return artifact.prd;

  }

  return artifact;

};

const getLatestArtifacts = (messages = []) => {

  const artifacts = {

    prd: null,

    user_stories: null,

    feature_prioritization: null,

  };

  messages.forEach((message) => {

    if (!message) return;

    const artifact = unwrapArtifact(

      message.artifact ??

      message.generatedArtifact ??

      message.generated_artifact

    );

    const type = String(

      message.artifactType ??

      message.artifact_type ??

      message.type ??

      ''

    ).toLowerCase();

    if (!artifact) return;

    if (

      type.includes('prd') ||

      (!type && (

        artifact.functional_requirements ||

        artifact.problem_statement

      ))

    ) {

      artifacts.prd = artifact;

    } else if (

      type.includes('user_story') ||

      type.includes('user-stor') ||

      type.includes('user stor')

    ) {

      artifacts.user_stories = artifact;

    } else if (type.includes('priorit')) {

      artifacts.feature_prioritization = artifact;

    }

  });

  return artifacts;

};

const normalizeSavedMessages = (message, index) => {

  const baseId = message?.id ?? message?._id ?? `saved-${index}`;

  const at =

    message?.at ??

    message?.generated_at ??

    message?.created_at ??

    new Date().toISOString();

  const conversationId =

    message?.conversationId ?? message?.conversation_id ?? null;

  const artifactType =

    message?.artifactType ??

    message?.artifact_type ??

    message?.artifact_type_name ??

    null;

  const artifact = unwrapArtifact(

    message?.artifact ??

    message?.generatedArtifact ??

    message?.generated_artifact

  );

  const agentUsed = message?.agentUsed ?? message?.agent_used ?? null;

  const common = { at, conversationId };

  // Older records sometimes store the user's prompt and AI reply together.

  // Expand them into two messages so neither side disappears in the UI.

  if (message?.user_message || message?.assistant_message) {

    const normalized = [];

    if (message.user_message) {

      normalized.push({

        ...common,

        id: `${baseId}-user`,

        role: 'user',

        text: String(message.user_message),

      });

    }

    if (message.assistant_message) {

      normalized.push({

        ...common,

        id: `${baseId}-assistant`,

        role: 'assistant',

        text: String(message.assistant_message),

        artifactType,

        artifact,

        agentUsed,

      });

    }

    return normalized;

  }

  return [{

    ...message,

    ...common,

    id: baseId,

    role: message?.role ?? 'assistant',

    text: String(message?.text ?? message?.content ?? ''),

    artifactType,

    artifact,

    agentUsed,

  }];

};

// ---------------------------------------------------------

// COMPONENT

// ---------------------------------------------------------

const buildLegacyConversationSummaries = (messages = []) => {

  const groups = new Map();

  messages.forEach((rawMessage, index) => {

    const normalizedMessages = normalizeSavedMessages(rawMessage, index);

    normalizedMessages.forEach((message) => {

      const conversationId =

        message.conversationId ||

        message.conversation_id ||

        'legacy-conversation';

      message.conversationId = conversationId;

      if (!groups.has(conversationId)) groups.set(conversationId, []);

      groups.get(conversationId).push(message);

    });

  });

  return Array.from(groups.entries())

    .map(([conversationId, items]) => {

      const firstUserMessage = items.find((item) => item.role === 'user');

      const latest = items[items.length - 1];

      const title = (firstUserMessage?.text || 'Saved conversation')

        .replace(/\s+/g, ' ')

        .trim()

        .slice(0, 72);

      return {

        conversationId,

        title: title || 'Saved conversation',

        createdAt: items[0]?.at || new Date().toISOString(),

        updatedAt: latest?.at || items[0]?.at || new Date().toISOString(),

        messageCount: items.length,

        preview: latest?.text || '',

        messages: items,

      };

    })

    .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));

};

export default function Chat() {

  const { raw, derived, analysis, refresh } = useAppData();

  const [messages, setMessages] = useState([WELCOME]);

  const [conversations, setConversations] = useState([]);

  const [activeConversationTitle, setActiveConversationTitle] = useState('New chat');

  const [historyLoading, setHistoryLoading] = useState(true);

  const [input, setInput] = useState('');

  const [thinking, setThinking] = useState(false);

  const [error, setError] = useState('');

  const bottomRef = useRef(null);

  const conversationIdRef = useRef(

    `conversation-${Date.now()}`

  );

  // -------------------------------------------------------

  // RESTORE CONVERSATION LIST AND MOST RECENT CHAT

  // -------------------------------------------------------

  const unwrapResponseData = (response) =>

    response?.data?.data ?? response?.data ?? [];

  const loadConversations = async () => {

    if (typeof apiClient.chat.getConversations !== 'function') return [];

    const response = await apiClient.chat.getConversations();

    if (!response?.success) {

      throw new Error(response?.message || 'Could not load chat history.');

    }

    const data = unwrapResponseData(response);

    const items = Array.isArray(data) ? data : data?.items || data?.conversations || [];

    setConversations(items);

    return items;

  };

  const selectConversation = async (conversation) => {

    if (!conversation?.conversationId || thinking) return;

    setError('');

    setHistoryLoading(true);

    try {

      let savedMessages = Array.isArray(conversation.messages)

        ? conversation.messages

        : null;

      if (!savedMessages) {

        const response = await apiClient.chat.getConversation(conversation.conversationId);

        if (!response?.success) {

          throw new Error(response?.message || 'Could not open conversation.');

        }

        const data = unwrapResponseData(response);

        savedMessages = Array.isArray(data)

          ? data

          : data?.messages || data?.conversation?.messages || [];

      }

      // A legacy DB record can contain both user_message and assistant_message.

      // flatMap restores both as separate chat bubbles.

      const restored = savedMessages.flatMap(normalizeSavedMessages);

      conversationIdRef.current = conversation.conversationId;

      setActiveConversationTitle(conversation.title || 'New chat');

      setMessages([WELCOME, ...restored]);

    } catch (loadError) {

      setError(loadError.message || 'Could not open this conversation.');

    } finally {

      setHistoryLoading(false);

    }

  };

  useEffect(() => {

    let active = true;

    const restoreHistory = async () => {

      setHistoryLoading(true);

      setError('');

      let listedConversations = [];

      try {

        listedConversations = await loadConversations();

      } catch (listError) {

        // Older deployments may not expose the conversation index endpoint.

        console.warn('Conversation index unavailable; checking legacy history:', listError);

      }

      if (!active) return;

      if (listedConversations.length > 0) {

        await selectConversation(listedConversations[0]);

        return;

      }

      try {

        const legacy = await apiClient.chat.getHistory();

        if (!legacy?.success) {

          throw new Error(legacy?.message || 'Could not load saved messages.');

        }

        const legacyData = unwrapResponseData(legacy);

        const savedMessages = Array.isArray(legacyData)

          ? legacyData

          : legacyData?.messages || legacyData?.items || [];

        if (!active) return;

        if (savedMessages.length > 0) {

          const summaries = buildLegacyConversationSummaries(savedMessages);

          setConversations(summaries);

          const latestConversation = summaries[0];

          if (latestConversation) {

            conversationIdRef.current = latestConversation.conversationId;

            setActiveConversationTitle(latestConversation.title);

            setMessages([WELCOME, ...latestConversation.messages]);

          }

        } else {

          setConversations([]);

          setMessages([WELCOME]);

        }

      } catch (legacyError) {

        console.error('Could not restore chat history:', legacyError);

        if (active) {

          setError(legacyError.message || 'Could not load chat history.');

        }

      } finally {

        if (active) setHistoryLoading(false);

      }

    };

    restoreHistory();

    return () => {

      active = false;

    };

  }, []);

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

    const saveable = nextMessages

      .filter((message) => message.id !== 'welcome')

      .map((message) => ({

        ...message,

        conversationId: conversationIdRef.current,

      }));

    const firstUserMessage = saveable.find((message) => message.role === 'user');

    const title = activeConversationTitle === 'New chat'

      ? (firstUserMessage?.text || 'New chat').trim().slice(0, 72)

      : activeConversationTitle;

    const response = typeof apiClient.chat.saveConversation === 'function'

      ? await apiClient.chat.saveConversation(

          conversationIdRef.current,

          { title, messages: saveable }

        )

      : await apiClient.chat.saveHistory(saveable);

    if (response?.success === false) {

      console.error('Could not save chat history:', response.message);

      setError(response.message || 'Your conversation could not be saved.');

      return false;

    }

    setActiveConversationTitle(title);

    setConversations((current) => {

      const existing = current.filter(

        (item) => item.conversationId !== conversationIdRef.current

      );

      return [{

        conversationId: conversationIdRef.current,

        title,

        updatedAt: new Date().toISOString(),

        messageCount: saveable.length,

        preview: saveable[saveable.length - 1]?.text || '',

      }, ...existing];

    });

    window.dispatchEvent(new Event('stratov:chat-count-updated'));

    return true;

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

    generated_artifacts: {

      prd: generatedArtifacts.prd,

      user_stories: generatedArtifacts.user_stories,

      feature_prioritization: generatedArtifacts.feature_prioritization,

    },

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

      conversationId: conversationIdRef.current,

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

          conversationId: conversationIdRef.current,

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

        // The backend may assign/normalize the conversation ID. Keep it

        // for all following turns and persist it with the chat messages.

        if (aiData.conversation_id || aiData.conversationId) {

          conversationIdRef.current =

            aiData.conversation_id || aiData.conversationId;

          userMsg.conversationId = conversationIdRef.current;

        }

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

          artifactType:

            aiData.artifact_type ??

            aiData.artifactType ??

            aiData.generated_artifact_type ??

            null,

          artifact: unwrapArtifact(

            aiData.artifact ??

            aiData.generated_artifact ??

            aiData.result?.artifact ??

            null

          ),

          agentUsed: aiData.agent_used || null,

          intent: aiData.intent || null,

        };

      }

      reply.conversationId = conversationIdRef.current;

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

  const newConversation = () => {

    if (thinking) return;

    conversationIdRef.current = `conversation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    setActiveConversationTitle('New chat');

    setMessages([WELCOME]);

    setInput('');

    setError('');

  };

  const deleteConversation = async (conversationId) => {

    if (thinking || !conversationId) return;

    const confirmed = window.confirm('Delete this conversation permanently?');

    if (!confirmed) return;

    try {

      const response = await apiClient.chat.deleteConversation(conversationId);

      if (!response?.success) {

        setError(response?.message || 'Could not delete this conversation.');

        return;

      }

      // Remove only the selected conversation. Do not reload the whole index here.

      setConversations((current) =>

        current.filter((item) => item.conversationId !== conversationId)

      );

      window.dispatchEvent(new Event('stratov:chat-count-updated'));

      // If the deleted conversation was open, reset only the chat view.

      if (conversationIdRef.current === conversationId) {

        conversationIdRef.current = `conversation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

        setActiveConversationTitle('New chat');

        setMessages([WELCOME]);

        setInput('');

        setError('');

      }

    } catch (err) {

      console.error('Delete conversation failed:', err);

      setError(

        err.response?.data?.message ||

        err.message ||

        'Could not delete this conversation.'

      );

    }

  };

  // UI

  // -------------------------------------------------------

  return (

    <div className="grid h-[calc(100dvh-7rem)] min-h-[22rem] min-w-0 grid-cols-1 grid-rows-[12rem_minmax(0,1fr)] gap-4 sm:grid-rows-[13rem_minmax(0,1fr)] lg:grid-cols-[280px_minmax(0,1fr)] lg:grid-rows-1">

      {/* SIDEBAR */}

      <aside className="card flex min-h-0 max-h-48 min-w-0 flex-col gap-3 overflow-hidden p-3 sm:max-h-52 lg:max-h-none">

        <Button

          onClick={newConversation}

          variant="outline"

          className="w-full justify-start"

          disabled={thinking}

        >

          <Plus size={16} />

          New chat

        </Button>

        <div className="min-h-0 flex-1 overflow-y-auto">

          <div className="mb-2 flex items-center justify-between px-1">

            <p className="text-xs font-semibold uppercase tracking-wide text-navy-500">

              Recent conversations

            </p>

            {historyLoading && (

              <span className="text-[10px] text-navy-400">Loading…</span>

            )}

          </div>

          {conversations.length === 0 && !historyLoading ? (

            <p className="px-2 py-3 text-xs text-navy-500">

              Your saved chats will appear here.

            </p>

          ) : (

            <ul className="space-y-1">

              {conversations.map((conversation) => {

                const active = conversation.conversationId === conversationIdRef.current;

                return (

                  <li key={conversation.conversationId} className="group flex items-center gap-1">

                    <button

                      type="button"

                      onClick={() => selectConversation(conversation)}

                      disabled={thinking}

                      className={`min-w-0 flex-1 rounded-lg px-2.5 py-2 text-left text-xs transition ${

                        active

                          ? 'bg-indigo-50 text-accent-700 dark:bg-indigo-500/15 dark:text-indigo-200'

                          : 'hover:bg-slate-50 dark:hover:bg-navy-700/60'

                      }`}

                    >

                      <span className="block truncate font-medium">

                        {conversation.title || 'New chat'}

                      </span>

                      {conversation.preview && (

                        <span className="mt-0.5 block truncate text-[10px] text-navy-500">

                          {conversation.preview}

                        </span>

                      )}

                    </button>

                    <button

                      type="button"

                      onClick={() => deleteConversation(conversation.conversationId)}

                      disabled={thinking}

                      title="Delete conversation"

                      aria-label={`Delete ${conversation.title || 'conversation'}`}

                      className="rounded p-1.5 text-slate-500 transition hover:bg-rose-50 hover:text-rose-600 focus:opacity-100 dark:text-slate-300 dark:hover:bg-rose-950/30"

                    >

                      <Trash2 size={13} />

                    </button>

                  </li>

                );

              })}

            </ul>

          )}

        </div>

        <div className="hidden border-t border-slate-200 pt-3 dark:border-navy-700 lg:block">

          <p className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-navy-500">

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

        <div className="hidden items-start gap-2 rounded-lg bg-slate-50 p-3 text-xs text-navy-500 dark:bg-navy-900/40 lg:flex">

          <Info size={14} className="mt-0.5 shrink-0" />

          {isMockMode

            ? 'Demo mode: responses use local workspace data.'

            : 'AI mode: powered by your unified Product Assistant and specialized AI agents.'}

        </div>

      </aside>

      {/* CONVERSATION */}

      <section className="card flex min-h-0 min-w-0 flex-col overflow-hidden">

        {/* HEADER */}

        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-navy-700">

          <div>

            <p className="text-sm font-semibold">

              {activeConversationTitle === 'New chat' ? 'Product Copilot' : activeConversationTitle}

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
