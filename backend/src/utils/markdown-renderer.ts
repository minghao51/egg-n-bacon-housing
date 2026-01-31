/**
 * markdown-renderer.ts
 * Convert markdown to HTML with proper table support
 */

import { highlightCodeBlocks } from './syntax-highlight';

export interface MarkdownResult {
  html: string;
  tables: Array<{ id: string; markdown: string }>;
}

export async function markdownToHtml(markdown: string, useSyntaxHighlighting: boolean = true): Promise<string> {
  let html = markdown;

  // STEP 1: Convert formula code blocks to LaTeX format BEFORE processing
  // This must happen before code block processing
  // Pattern: "**Formula:**" followed by ```...``` code block
  html = html.replace(/\*\*Formula:\*\*\s*\n```([\s\S]*?)```/gm, (match, formulaContent) => {
    // Strip leading/trailing whitespace and newlines
    const trimmedFormula = formulaContent.trim();

    // Convert to LaTeX block math format
    return `$$\n${trimmedFormula}\n$$`;
  });

  // STEP 2: Preserve LaTeX math formulas before HTML escaping
  const mathFormulas: Array<{ placeholder: string; formula: string }> = [];

  // Block math: $$...$$ or \[...\]
  html = html.replace(/\$\$[\s\S]*?\$\$/g, (match) => {
    const placeholder = `___MATH_BLOCK_${mathFormulas.length}___`;
    mathFormulas.push({ placeholder, formula: match });
    return placeholder;
  });

  html = html.replace(/\\[\[\]]/g, (match) => {
    // This is a simplified approach - in real usage, we'd need to track pairs
    return match;
  });

  // Inline math: $...$ or \(...\)
  html = html.replace(/\$[^$\n]+\$/g, (match) => {
    const placeholder = `___MATH_INLINE_${mathFormulas.length}___`;
    mathFormulas.push({ placeholder, formula: match });
    return placeholder;
  });

  // Escape HTML entities first to prevent XSS (but skip math placeholders)
  html = html.replace(/&/g, '&amp;');
  html = html.replace(/</g, '&lt;');
  html = html.replace(/>/g, '&gt;');

  // Restore math formulas
  mathFormulas.forEach(({ placeholder, formula }) => {
    html = html.replace(placeholder, formula);
  });

  // Code blocks with syntax highlighting (must be before other processing)
  if (useSyntaxHighlighting) {
    // Use Shiki for syntax highlighting
    html = await highlightCodeBlocks(html, false); // Theme will be handled by CSS
  } else {
    // Fallback to simple code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
    });
  }

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers with IDs (for TOC anchoring)
  html = html.replace(/^###\s+(.+?)\s+\{#([\w-]+)\}$/gm, '<h3 id="$2">$1</h3>');
  html = html.replace(/^##\s+(.+?)\s+\{#([\w-]+)\}$/gm, '<h2 id="$2">$1</h2>');
  html = html.replace(/^#\s+(.+?)\s+\{#([\w-]+)\}$/gm, '<h1 id="$2">$1</h1>');

  // Headers without IDs (fallback)
  html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');

  // Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Blockquotes
  html = html.replace(/^&gt;\s+(.+)$/gm, '<blockquote>$1</blockquote>');

  // Tables
  html = convertTables(html);

  // Unordered lists
  html = html.replace(/^\-\s+(.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

  // Ordered lists
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2">$1</a>');

  // Images
  html = html.replace(/!\[([^\]]*)\]\(([^\)]+)\)/g, '<img src="$2" alt="$1" loading="lazy" />');

  // Horizontal rules
  html = html.replace(/^---$/gm, '<hr />');

  // Line breaks and paragraphs
  html = html.replace(/\n\n+/g, '</p><p>');
  html = `<p>${html}</p>`;

  // Clean up empty paragraphs
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<h[1-6]>)/g, '$1');
  html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ul>)/g, '$1');
  html = html.replace(/(<\/ul>)<\/p>/g, '$1');
  html = html.replace(/<p>(<ol>)/g, '$1');
  html = html.replace(/(<\/ol>)<\/p>/g, '$1');
  html = html.replace(/<p>(<pre>)/g, '$1');
  html = html.replace(/(<\/pre>)<\/p>/g, '$1');
  html = html.replace(/<p>(<blockquote>)/g, '$1');
  html = html.replace(/(<\/blockquote>)<\/p>/g, '$1');
  html = html.replace(/<p>(<table>)/g, '$1');
  html = html.replace(/(<\/table>)<\/p>/g, '$1');

  return html;
}

function convertTables(markdown: string): string {
  // Match markdown tables
  const tableRegex = /(\|[^\n]+\|\n\|[-:|\s]+\|\n(?:\|[^\n]+\|\n?)+)/g;

  return markdown.replace(tableRegex, (match) => {
    const rows = match.trim().split('\n');

    // Extract header row
    const headerRow = rows[0];
    const headers = headerRow.split('|').filter(cell => cell.trim() !== '');

    // Extract separator row (for alignment)
    const separatorRow = rows[1];
    const alignments = separatorRow.split('|').filter(cell => cell.trim() !== '');

    // Extract data rows
    const dataRows = rows.slice(2);
    const data = dataRows.map(row =>
      row.split('|').filter(cell => cell.trim() !== '')
    );

    // Build HTML table
    let html = '<table>';

    // Header
    html += '<thead><tr>';
    headers.forEach((header, index) => {
      const align = alignments[index]?.includes(':') ? (alignments[index].startsWith(':') && alignments[index].endsWith(':') ? 'center' : (alignments[index].startsWith(':') ? 'left' : 'right')) : 'left';
      html += `<th style="text-align: ${align}">${header.trim()}</th>`;
    });
    html += '</tr></thead>';

    // Body
    html += '<tbody>';
    data.forEach(row => {
      html += '<tr>';
      row.forEach(cell => {
        html += `<td>${cell.trim()}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';

    return html;
  });
}

/**
 * Convert markdown to HTML and extract tables for inline chart rendering
 * @param markdown - Markdown content
 * @param useSyntaxHighlighting - Whether to use syntax highlighting
 * @returns HTML with chart placeholders + extracted table data
 */
export async function markdownToHtmlWithTables(
  markdown: string,
  useSyntaxHighlighting: boolean = true
): Promise<MarkdownResult> {
  const tables: Array<{ id: string; markdown: string }> = [];
  let processedMarkdown = markdown;
  let tableIndex = 0;

  // Extract tables and add placeholders AFTER them (keep tables in HTML)
  const tableRegex = /(\|[^\n]+\|\n\|[-:|\s]+\|\n(?:\|[^\n]+\|\n?)+)/g;

  processedMarkdown = processedMarkdown.replace(tableRegex, (match) => {
    const tableId = `chart-placeholder-${tableIndex}`;
    tables.push({
      id: tableId,
      markdown: match.trim()
    });
    tableIndex++;

    // Return original table markdown + placeholder div after it
    return `${match}\n<div id="${tableId}" class="chart-placeholder" data-chart-index="${tableIndex - 1}"></div>`;
  });

  // Convert to HTML (tables will be rendered normally)
  const html = await markdownToHtml(processedMarkdown, useSyntaxHighlighting);

  return {
    html,
    tables
  };
}
