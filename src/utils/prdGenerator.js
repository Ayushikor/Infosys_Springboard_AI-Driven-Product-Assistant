// Local template-based PRD generation. No AI model is called.
export const SECTION_KEYS = [
  'executiveSummary', 'problemStatement', 'goals', 'targetUsers', 'userStories',
  'functionalRequirements', 'nonFunctionalRequirements', 'acceptanceCriteria',
  'successMetrics', 'risks',
];

export const SECTION_TITLES = {
  executiveSummary: 'Executive Summary',
  problemStatement: 'Problem Statement',
  goals: 'Goals and Objectives',
  targetUsers: 'Target Users',
  userStories: 'User Stories',
  functionalRequirements: 'Functional Requirements',
  nonFunctionalRequirements: 'Non-Functional Requirements',
  acceptanceCriteria: 'Acceptance Criteria',
  successMetrics: 'Success Metrics',
  risks: 'Risks and Dependencies',
};

export const generatePrdContent = ({ feature, feedbackForTheme = [], rice, owner = 'Product team' }) => {
  const count = feedbackForTheme.length;
  const customers = [...new Set(feedbackForTheme.map((f) => f.customer))];
  const topQuotes = feedbackForTheme.slice(0, 3).map((f) => `- ${f.title} (${f.customer}, ${f.votes} votes)`).join('\n') || '- No linked feedback yet.';
  const name = feature.name;
  const theme = feature.theme || 'General';

  return {
    executiveSummary: `This PRD proposes "${name}" to address feedback in the ${theme} area. Current RICE score is ${rice ?? 'n/a'}. Owner: ${owner}.`,
    problemStatement: `${count} feedback record(s) from ${customers.length} customer(s) relate to ${theme.toLowerCase()}. Representative signals:\n${topQuotes}`,
    goals: `- Deliver "${name}" within the planned roadmap window.\n- Reduce related support tickets by at least 20% within one quarter.\n- Maintain or improve the current satisfaction score for affected customers.`,
    targetUsers: `- Primary: Customers and admins for whom ${theme.toLowerCase()} is a daily concern.\n- Secondary: Support and success teams handling related tickets.`,
    userStories: `- As a product manager, I want ${name.toLowerCase()} so I can meet customer expectations.\n- As an admin, I want ${name.toLowerCase()} so my team can work without friction.\n- As a support agent, I want fewer escalations about ${theme.toLowerCase()}.`,
    functionalRequirements: `- FR-1: The system shall support the core behavior described in "${name}".\n- FR-2: Changes shall be visible to all authorized users of the workspace.\n- FR-3: Relevant events shall be logged for auditing.`,
    nonFunctionalRequirements: `- NFR-1: Pages affected should respond within 2 seconds at p95.\n- NFR-2: Feature must meet WCAG 2.1 AA accessibility guidelines.\n- NFR-3: Data must be encrypted in transit and at rest.`,
    acceptanceCriteria: `- Given an authorized user, when they use ${name.toLowerCase()}, then the expected outcome occurs.\n- Given an invalid input, then a clear error message is shown.\n- Regression tests cover the primary flow.`,
    successMetrics: `- Adoption: 40% of active users within 60 days of release.\n- Support volume for ${theme.toLowerCase()} reduced by 20%.\n- Positive sentiment share increased by 10 points.`,
    risks: `- Dependency on platform team capacity.\n- Scope creep if edge cases are not prioritized.\n- Data migration effort for existing records.`,
  };
};

export const contentToMarkdown = (title, content) => {
  const body = SECTION_KEYS.map((k) => `## ${SECTION_TITLES[k]}\n\n${content[k] || '_Not yet written._'}`).join('\n\n');
  return `# ${title}\n\n${body}\n`;
};

export const contentToText = (title, content) => {
  const body = SECTION_KEYS.map((k) => `${SECTION_TITLES[k].toUpperCase()}\n${'-'.repeat(SECTION_TITLES[k].length)}\n${content[k] || 'Not yet written.'}`).join('\n\n');
  return `${title}\n${'='.repeat(title.length)}\n\n${body}\n`;
};
