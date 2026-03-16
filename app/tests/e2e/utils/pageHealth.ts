import { expect, type Page } from '@playwright/test';

type IgnorePattern = RegExp | string;

interface PageHealthOptions {
  ignoreConsoleErrors?: IgnorePattern[];
  ignoreConsoleWarnings?: IgnorePattern[];
  ignorePageErrors?: IgnorePattern[];
  ignoreFailedRequests?: IgnorePattern[];
  failOnConsoleWarnings?: boolean;
}

function matchesPattern(value: string, patterns: IgnorePattern[] = []): boolean {
  return patterns.some((pattern) =>
    typeof pattern === 'string' ? value.includes(pattern) : pattern.test(value),
  );
}

function isIgnorableFailedRequest(url: string, status: number, patterns: IgnorePattern[] = []): boolean {
  if (
    status === 404 &&
    /\/(?:favicon(?:-\d+x\d+)?\.(?:ico|png|svg)|apple-touch-icon(?:-precomposed)?\.png)(?:\?|$)/.test(url)
  ) {
    return true;
  }

  return matchesPattern(`${status} ${url}`, patterns) || matchesPattern(url, patterns);
}

export async function expectPageToLoadWithoutErrors(
  page: Page,
  url: string,
  options: PageHealthOptions = {},
): Promise<void> {
  const consoleErrors: string[] = [];
  const consoleWarnings: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];

  page.on('console', (msg) => {
    const text = msg.text();

    if (msg.type() === 'warning') {
      if (!matchesPattern(text, options.ignoreConsoleWarnings)) {
        consoleWarnings.push(text);
      }
      return;
    }

    if (msg.type() !== 'error') {
      return;
    }

    if (text.startsWith('Failed to load resource: the server responded with a status of')) {
      return;
    }

    if (!matchesPattern(text, options.ignoreConsoleErrors)) {
      consoleErrors.push(text);
    }
  });

  page.on('pageerror', (error) => {
    const text = error.message;
    if (!matchesPattern(text, options.ignorePageErrors)) {
      pageErrors.push(text);
    }
  });

  page.on('response', (response) => {
    if (response.status() < 400) {
      return;
    }

    const request = response.request();
    if (request.resourceType() === 'document' && response.status() >= 500) {
      failedRequests.push(`${response.status()} ${response.url()}`);
      return;
    }

    if (!isIgnorableFailedRequest(response.url(), response.status(), options.ignoreFailedRequests)) {
      failedRequests.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto(url);
  await page.waitForLoadState('networkidle');

  expect(consoleErrors, `Unexpected console errors on ${url}`).toEqual([]);
  if (options.failOnConsoleWarnings) {
    expect(consoleWarnings, `Unexpected console warnings on ${url}`).toEqual([]);
  }
  expect(pageErrors, `Unexpected uncaught page errors on ${url}`).toEqual([]);
  expect(failedRequests, `Unexpected failed requests on ${url}`).toEqual([]);
}
