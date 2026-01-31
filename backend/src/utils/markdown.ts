import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the docs/analytics directory (relative to backend directory)
const ANALYTICS_DOCS_PATH = path.resolve(
  path.join(__dirname, '../../../docs/analytics')
);

export interface MarkdownFile {
  slug: string;
  title: string;
  content: string;
  frontmatter?: Record<string, any>;
}

/**
 * Get list of all markdown files in docs/analytics
 */
export function getAnalyticsDocs(): MarkdownFile[] {
  if (!fs.existsSync(ANALYTICS_DOCS_PATH)) {
    console.error(`Analytics docs directory not found: ${ANALYTICS_DOCS_PATH}`);
    return [];
  }

  const files = fs.readdirSync(ANALYTICS_DOCS_PATH);
  const markdownFiles = files.filter((f) => f.endsWith('.md'));

  return markdownFiles.map((filename) => {
    const slug = filename.replace('.md', '');
    const filepath = path.join(ANALYTICS_DOCS_PATH, filename);
    const content = fs.readFileSync(filepath, 'utf-8');

    // Extract title from first h1 or use filename
    const titleMatch = content.match(/^#\s+(.+)$/m);
    const title = titleMatch ? titleMatch[1] : slug;

    // Extract frontmatter if present
    let frontmatter: Record<string, any> | undefined;
    const frontmatterMatch = content.match(/^\-\-\-\n(.+?)\n\-\-\-\n/s);
    if (frontmatterMatch) {
      try {
        // Simple YAML parser for basic frontmatter
        frontmatterMatch[1].split('\n').forEach((line) => {
          const [key, ...valueParts] = line.split(':');
          if (key && valueParts.length > 0) {
            const value = valueParts.join(':').trim();
            frontmatter = frontmatter || {};
            frontmatter[key.trim()] = value;
          }
        });
      } catch (e) {
        console.warn('Failed to parse frontmatter', e);
      }
    }

    return {
      slug,
      title,
      content,
      frontmatter,
    };
  });
}

/**
 * Get a specific markdown file by slug
 */
export function getAnalyticsDoc(slug: string): MarkdownFile | null {
  const docs = getAnalyticsDocs();
  return docs.find((doc) => doc.slug === slug) || null;
}

/**
 * Get all slugs
 */
export function getAnalyticsSlugs(): string[] {
  return getAnalyticsDocs().map((doc) => doc.slug);
}

/**
 * Strip the first H1 heading from markdown content
 * Used to avoid duplicate titles when page header already shows title
 */
export function stripTitle(markdown: string): string {
  // Remove first H1 with optional leading whitespace
  return markdown.replace(/^#\s+.+$/m, '').trim();
}
