/**
 * syntax-highlight.ts
 * Syntax highlighting for code blocks using Shiki
 */

import { codeToHtml } from 'shiki';

interface HighlightResult {
  html: string;
  css?: string;
}

let shikiInitialized = false;

/**
 * Initialize Shiki with the theme
 * This is cached after first call
 */
async function initializeShiki() {
  if (shikiInitialized) return;

  try {
    // Pre-load common languages for better performance
    await codeToHtml('', {
      lang: 'python',
      themes: { light: 'github-light', dark: 'github-dark' }
    });
    shikiInitialized = true;
  } catch (error) {
    console.error('Failed to initialize Shiki:', error);
  }
}

/**
 * Highlight code blocks with syntax highlighting
 * @param code - The code to highlight
 * @param lang - The programming language
 * @param isDark - Whether to use dark theme
 * @returns HTML with syntax highlighting
 */
export async function highlightCode(
  code: string,
  lang: string = 'text',
  isDark: boolean = false
): Promise<string> {
  try {
    await initializeShiki();

    const html = await codeToHtml(code, {
      lang: lang || 'text',
      themes: {
        light: 'github-light',
        dark: 'github-dark'
      },
      defaultTheme: isDark ? 'dark' : 'light'
    });

    return html;
  } catch (error) {
    console.warn(`Failed to highlight ${lang} code, falling back to plain text:`, error);
    // Fallback: return escaped code in a pre/code block
    const escaped = code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    return `<pre><code class="language-${lang}">${escaped}</code></pre>`;
  }
}

/**
 * Process markdown and replace code blocks with highlighted versions
 * @param markdown - The markdown content
 * @param isDark - Whether to use dark theme
 * @returns HTML with syntax-highlighted code blocks
 */
export async function highlightCodeBlocks(
  markdown: string,
  isDark: boolean = false
): Promise<string> {
  // Match code blocks: ```lang\ncode\n```
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;

  const replacements: Array<{ match: string; replacement: string }> = [];

  let match;
  while ((match = codeBlockRegex.exec(markdown)) !== null) {
    const fullMatch = match[0];
    const lang = match[1] || 'text';
    const code = match[2];

    // Store for async replacement
    replacements.push({
      match: fullMatch,
      replacement: await highlightCode(code, lang, isDark)
    });
  }

  // Replace all code blocks
  let result = markdown;
  for (const { match, replacement } of replacements) {
    result = result.replace(match, replacement);
  }

  return result;
}

/**
 * Simple synchronous version for fallback
 * This doesn't do syntax highlighting but preserves the code
 */
export function escapeCode(code: string, lang: string = 'text'): string {
  const escaped = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return `<pre class="shiki"><code class="language-${lang}">${escaped}</code></pre>`;
}
