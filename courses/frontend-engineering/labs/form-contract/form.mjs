/** Pure JavaScript form contract: never inject untrusted input into innerHTML. */
const ALLOWED_PLANS = new Set(['foundation', 'practitioner']);
export function validateEnrollment(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return { ok: false, errors: ['input must be an object'] };
  }
  const errors = [];
  const keys = Object.keys(input);
  if (keys.some(k => !['email', 'plan', 'acceptedTerms'].includes(k))) errors.push('unexpected field');
  if (typeof input.email !== 'string' || input.email.length > 254 ||
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email)) errors.push('invalid email');
  if (typeof input.plan !== 'string' || !ALLOWED_PLANS.has(input.plan)) errors.push('invalid plan');
  if (input.acceptedTerms !== true) errors.push('terms not accepted');
  return { ok: errors.length === 0, errors };
}
export function renderStatus(node, message) {
  if (!node || typeof node.textContent === 'undefined') throw new TypeError('text node required');
  node.textContent = String(message);
}
