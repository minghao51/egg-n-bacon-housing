/**
 * Minimal ambient declarations for Bun's built-in test module.
 *
 * The app has no `bun-types` dependency, but `tests/unit/**` is part of the
 * `astro check` program. These declarations keep the unit specs type-checked
 * without adding a dependency or pulling in all of Bun's ambient globals.
 * If `bun-types` is ever installed, delete this file.
 */
declare module "bun:test" {
  type AsyncFn = () => void | Promise<void>;

  interface Matchers {
    readonly not: Matchers;
    toBe(expected: unknown): void;
    toEqual(expected: unknown): void;
    toMatchObject(expected: unknown): void;
    toBeNull(): void;
    toBeUndefined(): void;
    toBeDefined(): void;
    toBeTruthy(): void;
    toBeFalsy(): void;
    toBeGreaterThan(expected: number): void;
    toBeGreaterThanOrEqual(expected: number): void;
    toBeLessThan(expected: number): void;
    toBeLessThanOrEqual(expected: number): void;
    toBeCloseTo(expected: number, precision?: number): void;
    toContain(expected: unknown): void;
    toHaveLength(expected: number): void;
    toThrow(expected?: string | RegExp | Error): void;
  }

  export function describe(name: string, fn: () => void): void;
  export function test(name: string, fn: AsyncFn): void;
  export function it(name: string, fn: AsyncFn): void;
  export function beforeEach(fn: AsyncFn): void;
  export function afterEach(fn: AsyncFn): void;
  export function expect(actual: unknown): Matchers;
}
