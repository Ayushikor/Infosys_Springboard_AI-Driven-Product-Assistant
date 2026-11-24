
// Local template-based PRD generation. No AI model is called.

export const SECTION_KEYS = [
  'executiveSummary',
  'problemStatement',
  'proposedSolution',
  'goals',
  'targetUsers',
  'userStories',
  'functionalRequirements',
  'nonFunctionalRequirements',
  'acceptanceCriteria',
  'successMetrics',
  'risks',
  'scope',
];

export const SECTION_TITLES = {
  executiveSummary: 'Executive Summary',
  problemStatement: 'Problem Statement',
  proposedSolution: 'Proposed Solution',
  goals: 'Goals and Objectives',
  targetUsers: 'Target Users',
  userStories: 'User Stories',
  functionalRequirements: 'Functional Requirements',
  nonFunctionalRequirements: 'Non-Functional Requirements',
  acceptanceCriteria: 'Acceptance Criteria',
  successMetrics: 'Success Metrics',
  risks: 'Risks and Dependencies',
  scope: 'Product Scope',
};

const SECTION_ALIASES = {
  executiveSummary: [
    'executiveSummary',
    'executive_summary',
    'overview',
    'summary',
  ],
  problemStatement: [
    'problemStatement',
    'problem_statement',
    'problem',
  ],
  proposedSolution: [
    'proposedSolution',
    'proposed_solution',
    'solution',
  ],
  goals: [
    'goals',
    'objectives',
    'goals_and_objectives',
  ],
  targetUsers: [
    'targetUsers',
    'target_users',
    'user_personas',
    'personas',
  ],
  userStories: [
    'userStories',
    'user_stories',
    'stories',
    'use_cases',
  ],
  functionalRequirements: [
    'functionalRequirements',
    'functional_requirements',
    'requirements',
    'features',
  ],
  nonFunctionalRequirements: [
    'nonFunctionalRequirements',
    'non_functional_requirements',
    'nfrs',
    'quality_attributes',
  ],
  acceptanceCriteria: [
    'acceptanceCriteria',
    'acceptance_criteria',
  ],
  successMetrics: [
    'successMetrics',
    'success_metrics',
    'metrics',
    'kpis',
  ],
  risks: [
    'risks',
    'risks_and_dependencies',
    'dependencies',
    'assumptions',
    'constraints',
  ],
  scope: [
    'scope',
    'product_scope',
    'project_scope',
    'mvp_scope',
  ],
};

const hasUsableValue = (value) =>
  value !== undefined &&
  value !== null &&
  value !== '';

/**
 * Converts backend snake_case PRD fields into
 * frontend camelCase section fields.
 * Preserves unknown fields and nested data.
 */
export const normalizePrdContent = (content = {}) => {
  if (
    !content ||
    typeof content !== 'object' ||
    Array.isArray(content)
  ) {
    return content;
  }

  const normalized = { ...content };

  for (const [target, aliases] of Object.entries(SECTION_ALIASES)) {
    const sourceKey = aliases.find(
      (key) =>
        Object.prototype.hasOwnProperty.call(content, key) &&
        hasUsableValue(content[key])
    );

    if (sourceKey) {
      normalized[target] = content[sourceKey];
    } else if (!hasUsableValue(normalized[target])) {
      normalized[target] = '';
    }
  }

  return normalized;
};

export const generatePrdContent = ({
  feature,
  feedbackForTheme = [],
  rice,
  owner = 'Product team',
}) => {
  const count = feedbackForTheme.length;

  const customers = [
    ...new Set(
      feedbackForTheme
        .map((f) => f.customer)
        .filter(Boolean)
    ),
  ];

  const topQuotes =
    feedbackForTheme
      .slice(0, 3)
      .map(
        (f) =>
          `- ${f.title} (${f.customer || 'Unknown customer'}, ${f.votes ?? 0} votes)`
      )
      .join('\n') || '- No linked feedback yet.';

  const name = feature?.name || 'Untitled feature';
  const theme = feature?.theme || 'General';

  return {
    executiveSummary: `This PRD proposes "${name}" to address feedback in the ${theme} area. Current RICE score is ${rice ?? 'n/a'}. Owner: ${owner}.`,

    problemStatement: `${count} feedback record(s) from ${customers.length} customer(s) relate to ${theme.toLowerCase()}. Representative signals:\n${topQuotes}`,

    proposedSolution: `Deliver ${name} as a focused product capability for the ${theme} area.`,

    goals: `- Deliver "${name}" within the planned roadmap window.\n- Reduce related support tickets by at least 20% within one quarter.\n- Maintain or improve the current satisfaction score for affected customers.`,

    targetUsers: `- Primary: Customers and admins for whom ${theme.toLowerCase()} is a daily concern.\n- Secondary: Support and success teams handling related tickets.`,

    userStories: `- As a product manager, I want ${name.toLowerCase()} so I can meet customer expectations.\n- As an admin, I want ${name.toLowerCase()} so my team can work without friction.\n- As a support agent, I want fewer escalations about ${theme.toLowerCase()}.`,

    functionalRequirements: `- FR-1: The system shall support the core behavior described in "${name}".\n- FR-2: Changes shall be visible to all authorized users of the workspace.\n- FR-3: Relevant events shall be logged for auditing.`,

    nonFunctionalRequirements: `- NFR-1: Pages affected should respond within 2 seconds at p95.\n- NFR-2: Feature must meet WCAG 2.1 AA accessibility guidelines.\n- NFR-3: Data must be encrypted in transit and at rest.`,

    acceptanceCriteria: `- Given an authorized user, when they use ${name.toLowerCase()}, then the expected outcome occurs.\n- Given an invalid input, then a clear error message is shown.\n- Regression tests cover the primary flow.`,

    successMetrics: `- Adoption: 40% of active users within 60 days of release.\n- Support volume for ${theme.toLowerCase()} reduced by 20%.\n- Positive sentiment share increased by 10 points.`,

    risks: `- Dependency on platform team capacity.\n- Scope creep if edge cases are not prioritized.\n- Data migration effort for existing records.`,

    scope: `MVP: Core ${name.toLowerCase()} workflow, access control, and audit logging.\nFuture: Advanced automation and expanded integrations.`,
  };
};

const toReadableText = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return 'Not yet written.';
  }

  if (typeof value === 'string') {
    return value;
  }

  if (Array.isArray(value)) {
    return value
      .map((item) =>
        typeof item === 'object' && item !== null
          ? Object.entries(item)
              .map(
                ([key, val]) =>
                  `${key}: ${toReadableText(val)}`
              )
              .join('; ')
          : String(item)
      )
      .map((line) => `- ${line}`)
      .join('\n');
  }

  if (typeof value === 'object') {
    return Object.entries(value)
      .map(
        ([key, val]) =>
          `${key.replace(/[_-]/g, ' ')}: ${toReadableText(val)}`
      )
      .join('\n');
  }

  return String(value);
};

export const contentToMarkdown = (title, content = {}) => {
  const normalized = normalizePrdContent(content);

  const body = SECTION_KEYS
    .map(
      (key) =>
        `## ${SECTION_TITLES[key]}\n\n${toReadableText(normalized?.[key])}`
    )
    .join('\n\n');

  return `# ${title}\n\n${body}\n`;
};

export const contentToText = (title, content = {}) => {
  const normalized = normalizePrdContent(content);

  const body = SECTION_KEYS
    .map(
      (key) =>
        `${SECTION_TITLES[key].toUpperCase()}\n${'-'.repeat(SECTION_TITLES[key].length)}\n${toReadableText(normalized?.[key])}`
    )
    .join('\n\n');

  return `${title}\n${'='.repeat(String(title || '').length)}\n\n${body}\n`;
};
