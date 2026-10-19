// Seed data for a fresh install. New users start with an empty workspace
// (see mockApi.seedWorkspaceFor); the demo account gets this full dataset.
const DAY = 86400000;
const ago = (n) => new Date(Date.now() - n * DAY).toISOString();
const dateOnly = (n) => ago(n).slice(0, 10);

export const SEED_THEMES = [
  { id: 'th-ux', name: 'User Experience', keywords: ['ux', 'confusing', 'navigation', 'layout', 'intuitive', 'design', 'settings', 'onboarding', 'dark mode'], description: 'Usability, navigation and clarity of the interface.' },
  { id: 'th-perf', name: 'Performance', keywords: ['slow', 'loading', 'lag', 'timeout', 'speed', 'freeze', 'fast', 'times out'], description: 'Load times, responsiveness and stability.' },
  { id: 'th-auth', name: 'Authentication and Security', keywords: ['login', 'password', '2fa', 'security', 'sso', 'permission', 'access', 'saml'], description: 'Sign-in, access control and account safety.' },
  { id: 'th-reports', name: 'Reporting and Analytics', keywords: ['report', 'analytics', 'export', 'chart', 'dashboard', 'metrics', 'filter'], description: 'Dashboards, reports, and data exports.' },
  { id: 'th-integ', name: 'Integrations', keywords: ['slack', 'integration', 'api', 'webhook', 'jira', 'zapier', 'connect', 'sync'], description: 'Third-party tools and API connectivity.' },
  { id: 'th-mobile', name: 'Mobile Experience', keywords: ['mobile', 'android', 'ios', 'phone', 'notification', 'tablet', 'push'], description: 'Mobile app quality and push notifications.' },
  { id: 'th-billing', name: 'Billing', keywords: ['invoice', 'billing', 'price', 'pricing', 'charge', 'refund', 'subscription', 'payment', 'vat', 'tax'], description: 'Pricing, invoices, and payment issues.' },
];

export const SEED_FEEDBACK = [
  { id: 'fb-001', title: 'Dashboard takes forever to load', message: 'The main dashboard is slow to load with more than 10k rows. Often times out.', customer: 'Acme Corp', source: 'Support Ticket', createdAt: ago(2), sentiment: 'negative', theme: 'Performance', votes: 34 },
  { id: 'fb-002', title: 'Need Slack notifications', message: 'Would love to get alerts for new feedback directly in Slack channels.', customer: 'Brightline', source: 'Feature Request', createdAt: ago(3), sentiment: 'positive', theme: 'Integrations', votes: 58 },
  { id: 'fb-003', title: 'Login loop on Safari', message: 'After signing in on Safari the page redirects back to login repeatedly.', customer: 'Nimbus Labs', source: 'Bug Report', createdAt: ago(4), sentiment: 'negative', theme: 'Authentication and Security', votes: 22 },
  { id: 'fb-004', title: 'Export to CSV is confusing', message: 'I cannot find where to export reports. The menu layout is not intuitive.', customer: 'Orbit Retail', source: 'Survey', createdAt: ago(5), sentiment: 'negative', theme: 'User Experience', votes: 17 },
  { id: 'fb-005', title: 'Want 2FA via authenticator app', message: 'Please add two-factor authentication support using TOTP apps.', customer: 'Helix Finance', source: 'Feature Request', createdAt: ago(6), sentiment: 'neutral', theme: 'Authentication and Security', votes: 46 },
  { id: 'fb-006', title: 'Mobile app crashes on Android 14', message: 'The Android app crashes when opening reports. Very frustrating.', customer: 'Pulse Health', source: 'Bug Report', createdAt: ago(7), sentiment: 'negative', theme: 'Mobile Experience', votes: 29 },
  { id: 'fb-007', title: 'Invoice PDF missing tax line', message: 'The billing invoice does not show the VAT breakdown. Accounting is asking.', customer: 'Acme Corp', source: 'Support Ticket', createdAt: ago(8), sentiment: 'negative', theme: 'Billing', votes: 12 },
  { id: 'fb-008', title: 'Custom dashboard filters', message: 'We need saved filters on dashboards so the team can reuse views.', customer: 'Quantum Ops', source: 'Feature Request', createdAt: ago(9), sentiment: 'positive', theme: 'Reporting and Analytics', votes: 41 },
  { id: 'fb-009', title: 'Great onboarding flow', message: 'The new onboarding wizard made setup really easy. Love the progress indicator.', customer: 'Lumen Studio', source: 'Survey', createdAt: ago(10), sentiment: 'positive', theme: 'User Experience', votes: 9 },
  { id: 'fb-010', title: 'Reports page times out', message: 'Generating a monthly analytics report times out after about 60 seconds.', customer: 'Brightline', source: 'Support Ticket', createdAt: ago(11), sentiment: 'negative', theme: 'Performance', votes: 31 },
  { id: 'fb-011', title: 'Advanced analytics exports', message: 'Please allow exporting charts as PNG and raw data as Excel for stakeholder decks.', customer: 'Helix Finance', source: 'Feature Request', createdAt: ago(12), sentiment: 'neutral', theme: 'Reporting and Analytics', votes: 37 },
  { id: 'fb-012', title: 'SSO setup is painful', message: 'Configuring SAML SSO took our IT team three days. Needs better docs and errors.', customer: 'Nimbus Labs', source: 'Support Ticket', createdAt: ago(13), sentiment: 'negative', theme: 'Authentication and Security', votes: 26 },
  { id: 'fb-013', title: 'Jira integration sync delay', message: 'Jira tickets take about 20 minutes to sync, so our tracking is always behind.', customer: 'Pulse Health', source: 'Bug Report', createdAt: ago(14), sentiment: 'negative', theme: 'Integrations', votes: 19 },
  { id: 'fb-014', title: 'Push notifications unreliable', message: 'iOS push notifications arrive hours late or not at all.', customer: 'Lumen Studio', source: 'Survey', createdAt: ago(15), sentiment: 'negative', theme: 'Mobile Experience', votes: 24 },
  { id: 'fb-015', title: 'Pricing tier is unclear', message: 'Not sure which plan includes API access. The pricing page needs clarity.', customer: 'Orbit Retail', source: 'Survey', createdAt: ago(16), sentiment: 'neutral', theme: 'Billing', votes: 15 },
  { id: 'fb-016', title: 'Search is fast now', message: 'Search results return instantly after the last release. Really nice improvement.', customer: 'Quantum Ops', source: 'Survey', createdAt: ago(17), sentiment: 'positive', theme: 'Performance', votes: 7 },
  { id: 'fb-017', title: 'Webhook retries needed', message: 'Our webhook endpoints fail intermittently and we have no retry mechanism.', customer: 'Helix Finance', source: 'Feature Request', createdAt: ago(18), sentiment: 'neutral', theme: 'Integrations', votes: 21 },
  { id: 'fb-018', title: 'Hard to find settings', message: 'The settings menu is buried. Took me ages to find the notification options.', customer: 'Acme Corp', source: 'Survey', createdAt: ago(19), sentiment: 'negative', theme: 'User Experience', votes: 14 },
  { id: 'fb-019', title: 'Refund process unclear', message: 'Requested a refund and the process was unclear. No status updates given.', customer: 'Nimbus Labs', source: 'Support Ticket', createdAt: ago(20), sentiment: 'negative', theme: 'Billing', votes: 11 },
  { id: 'fb-020', title: 'Dark mode please', message: 'Would be great to have a dark theme for late-night work. Loving the product otherwise.', customer: 'Lumen Studio', source: 'Feature Request', createdAt: ago(21), sentiment: 'positive', theme: 'User Experience', votes: 63 },
  { id: 'fb-021', title: 'Role-based permissions', message: 'Need granular permissions so contractors cannot see billing information.', customer: 'Brightline', source: 'Feature Request', createdAt: ago(22), sentiment: 'neutral', theme: 'Authentication and Security', votes: 33 },
  { id: 'fb-022', title: 'Tablet layout breaks', message: 'On iPad the sidebar overlaps the table and the buttons are unreachable.', customer: 'Pulse Health', source: 'Bug Report', createdAt: ago(23), sentiment: 'negative', theme: 'Mobile Experience', votes: 8 },
];

export const SEED_FEATURES = [
  { id: 'ft-001', name: 'Two-factor authentication', theme: 'Authentication and Security', reach: 1200, impact: 3, confidence: 0.9, effort: 5, status: 'In Progress', description: 'TOTP-based 2FA for all accounts.' },
  { id: 'ft-002', name: 'Faster dashboard loading', theme: 'Performance', reach: 2500, impact: 2, confidence: 0.8, effort: 8, status: 'Planned', description: 'Virtualized tables and query caching.' },
  { id: 'ft-003', name: 'Advanced analytics exports', theme: 'Reporting and Analytics', reach: 900, impact: 2, confidence: 0.7, effort: 3, status: 'Planned', description: 'PNG chart exports and Excel raw data export.' },
  { id: 'ft-004', name: 'Slack integration', theme: 'Integrations', reach: 1500, impact: 2, confidence: 0.85, effort: 4, status: 'Planned', description: 'Feedback alerts delivered to Slack channels.' },
  { id: 'ft-005', name: 'Mobile notifications', theme: 'Mobile Experience', reach: 800, impact: 1, confidence: 0.6, effort: 3, status: 'Backlog', description: 'Reliable push notifications on iOS and Android.' },
  { id: 'ft-006', name: 'Custom dashboard filters', theme: 'Reporting and Analytics', reach: 1100, impact: 2, confidence: 0.75, effort: 2, status: 'In Review', description: 'Saved, shareable dashboard filter presets.' },
  { id: 'ft-007', name: 'Dark mode', theme: 'User Experience', reach: 1800, impact: 1, confidence: 0.9, effort: 2, status: 'Completed', description: 'System-aware dark theme.' },
  { id: 'ft-008', name: 'Invoice tax breakdown', theme: 'Billing', reach: 400, impact: 1, confidence: 0.95, effort: 1, status: 'Planned', description: 'Show VAT/GST line items on invoices.' },
];

export const SEED_PRDS = [
  { id: 'prd-001', title: 'PRD: Two-factor authentication', featureId: 'ft-001', version: '1.2', status: 'Approved', createdAt: ago(30), updatedAt: ago(3), content: null },
  { id: 'prd-002', title: 'PRD: Slack integration', featureId: 'ft-004', version: '0.9', status: 'In Review', createdAt: ago(20), updatedAt: ago(1), content: null },
  { id: 'prd-003', title: 'PRD: Faster dashboard loading', featureId: 'ft-002', version: '1.0', status: 'Draft', createdAt: ago(10), updatedAt: ago(10), content: null },
  { id: 'prd-004', title: 'PRD: Custom dashboard filters', featureId: 'ft-006', version: '1.1', status: 'Approved', createdAt: ago(14), updatedAt: ago(5), content: null },
];

export const SEED_ROADMAP = [
  { id: 'rm-001', featureId: 'ft-001', name: 'Two-factor authentication', startDate: dateOnly(-10), targetDate: dateOnly(20), priority: 'High', status: 'In Progress', owner: 'Priya Sharma', theme: 'Authentication and Security' },
  { id: 'rm-002', featureId: 'ft-002', name: 'Faster dashboard loading', startDate: dateOnly(-20), targetDate: dateOnly(-2), priority: 'High', status: 'Planned', owner: 'Daniel Ortiz', theme: 'Performance' },
  { id: 'rm-003', featureId: 'ft-004', name: 'Slack integration', startDate: dateOnly(5), targetDate: dateOnly(45), priority: 'Medium', status: 'Planned', owner: 'Maya Chen', theme: 'Integrations' },
  { id: 'rm-004', featureId: 'ft-003', name: 'Advanced analytics exports', startDate: dateOnly(-45), targetDate: dateOnly(-5), priority: 'Medium', status: 'In Review', owner: 'Leo Martins', theme: 'Reporting and Analytics' },
  { id: 'rm-005', featureId: 'ft-005', name: 'Mobile notifications', startDate: dateOnly(30), targetDate: dateOnly(75), priority: 'Low', status: 'Planned', owner: 'Aisha Khan', theme: 'Mobile Experience' },
  { id: 'rm-006', featureId: 'ft-006', name: 'Custom dashboard filters', startDate: dateOnly(-30), targetDate: dateOnly(10), priority: 'High', status: 'In Review', owner: 'Maya Chen', theme: 'Reporting and Analytics' },
  { id: 'rm-007', featureId: 'ft-007', name: 'Dark mode', startDate: dateOnly(-90), targetDate: dateOnly(-60), priority: 'Low', status: 'Completed', owner: 'Priya Sharma', theme: 'User Experience' },
  { id: 'rm-008', featureId: 'ft-008', name: 'Invoice tax breakdown', startDate: dateOnly(-5), targetDate: dateOnly(14), priority: 'Medium', status: 'Planned', owner: 'Daniel Ortiz', theme: 'Billing' },
];

export const SEED_WORKSPACE = {
  id: 'ws-001',
  name: 'Customer Insights HQ',
  description: 'Central workspace for turning customer feedback into product decisions.',
  createdAt: ago(90),
};

export const SEED_ACTIVITY = [
  { id: 'act-1', text: 'Imported 22 feedback records from seed data', at: ago(1) },
  { id: 'act-2', text: 'PRD "Slack integration" moved to In Review', at: ago(1) },
  { id: 'act-3', text: 'Feature "Dark mode" marked Completed', at: ago(4) },
];
