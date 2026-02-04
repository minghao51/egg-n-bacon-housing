/**
 * formula-converter.ts
 * Convert plain text math formulas to LaTeX syntax
 */

/**
 * Convert plain text formula to LaTeX
 * @param formula - Plain text formula (e.g., "Growth (%) = (P_t - P_{t-1}) / P_{t-1} × 100")
 * @returns LaTeX string (e.g., "Growth (\\%) = \\frac{P_t - P_{t-1}}{P_{t-1}} \\times 100")
 */
export function convertToLaTeX(formula: string): string {
  let latex = formula;

  // Step 1: Escape special characters
  latex = latex.replace(/%/g, '\\%');  // Percent sign
  latex = latex.replace(/&/g, '\\&');  // Ampersand

  // Step 2: Convert subscripts (e.g., P_t, P_{t-1})
  // Handle both simple and complex subscripts
  latex = latex.replace(/([a-zA-Z])_([a-zA-Z0-9]+)/g, '$1_{$2}');
  latex = latex.replace(/([a-zA-Z])_\{([^}]+)\}/g, '$1_{$2}'); // Already wrapped

  // Step 3: Convert superscripts (e.g., x^2)
  // Wrap superscript in braces if not already
  latex = latex.replace(/\^([0-9a-zA-Z])([^{])/g, '^{$1}$2');
  latex = latex.replace(/([a-zA-Z])^\{([^}]+)\}/g, '$1^{$2}'); // Already wrapped

  // Step 4: Convert multiplication symbol
  latex = latex.replace(/×/g, '\\times ');

  // Step 5: Convert division to fractions
  // Pattern: (something) / (something else) or simple a / b
  // This is a simplified version - you may need to adjust based on your formulas
  const fractionPattern = /\(([^)]+)\)\s*\/\s*\(([^)]+)\)/g;
  latex = latex.replace(fractionPattern, (match, numerator, denominator) => {
    return `\\frac{${numerator.trim()}}{${denominator.trim()}}`;
  });

  // Handle simple division without parentheses: a / b
  // Be careful not to break URLs or other slashes
  const simpleFractionPattern = /([a-zA-Z0-9_{}]+)\s*\/\s*([a-zA-Z0-9_{}]+)(?![a-zA-Z])/g;
  latex = latex.replace(simpleFractionPattern, (match, numerator, denominator) => {
    // Only convert if it looks like math (has subscripts/superscripts or variables)
    if (numerator.includes('_') || numerator.includes('^') ||
        denominator.includes('_') || denominator.includes('^') ||
        /[a-zA-Z]{2,}/.test(numerator) || /[a-zA-Z]{2,}/.test(denominator)) {
      return `\\frac{${numerator}}{${denominator}}`;
    }
    return match;
  });

  // Step 6: Clean up spacing
  latex = latex.replace(/\s+/g, ' ').trim();
  latex = latex.replace(/\\times\s+/g, '\\times ');

  return latex;
}

/**
 * Check if a formula is complex enough to need LaTeX rendering
 * @param formula - Plain text formula
 * @returns True if formula should use LaTeX
 */
export function needsLaTeX(formula: string): boolean {
  // Needs LaTeX if it has:
  // - Subscripts (e.g., P_t)
  // - Superscripts (e.g., x^2)
  // - Division (e.g., a / b)
  // - Multiplication symbol (×)
  // - Multiple lines
  return /[_^×\/]|\\n/.test(formula);
}

/**
 * Extract formula from code block content
 * Handles multi-line formulas with "Where:" explanations
 * @param codeContent - Content from the code block
 * @returns Formula text without explanations
 */
export function extractFormula(codeContent: string): string {
  // Remove "Where:" lines and everything after
  const lines = codeContent.split('\n');
  const formulaLines: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    // Stop at "Where:" or similar explanation keywords
    if (trimmed.match(/^(Where|Note|For)/i)) {
      break;
    }
    formulaLines.push(line);
  }

  return formulaLines.join('\n').trim();
}
