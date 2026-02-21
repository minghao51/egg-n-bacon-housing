import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';

interface MarkdownContentProps {
  content: string;
}

/**
 * Secure markdown rendering component with XSS protection.
 * Uses react-markdown for parsing and DOMPurify for sanitization.
 */
export default function MarkdownContent({ content }: MarkdownContentProps) {
  // Sanitize content before rendering to prevent XSS attacks
  const sanitizedContent = DOMPurify.sanitize(content);

  return (
    <div className="prose dark:prose-invert max-w-none markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  );
}
