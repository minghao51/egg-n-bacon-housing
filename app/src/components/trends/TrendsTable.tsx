/**
 * Accessible monthly table for `/research/trends`.
 *
 * This is the reading of the series that needs no chart gesture: every month in
 * the selected window, in calendar order, with its own price and transaction
 * count. A month with no published value says `N/A`; it never says `0` and it is
 * never skipped, so the calendar stays visible.
 */

import { formatTrendNumber, type TrendSeries } from "@/utils/trend-series";

export interface TrendsTableProps {
  series: TrendSeries;
  /** Wrapper id, so the charts can reference this table as their long description. */
  id: string;
}

export default function TrendsTable({ series, id }: TrendsTableProps) {
  const caption = `Monthly median transaction price and transaction count for ${series.label}.`;

  return (
    <section id={id} aria-labelledby={`${id}-heading`} className="mt-10">
      <h2 id={`${id}-heading`} className="text-xl font-bold text-foreground">
        Every month in the selected window
      </h2>
      <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
        Monthly median transaction price in nominal SGD and the count of included
        transactions. <span className="font-bold text-foreground">N/A</span> means
        the published asset carries no value for that month; it is not a zero and
        it is not an estimate. Months are never skipped, so a gap in the series
        stays visible as a gap.
      </p>

      {series.points.length === 0 ? (
        <p className="mt-4 rounded-lg border border-border bg-card p-5 text-sm text-foreground">
          No published month falls inside this window for {series.label}. The
          asset publishes no values here, which says nothing about whether sales
          happened — it is not a year of zero prices.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{caption}</caption>
            <thead>
              <tr className="border-b border-border text-left">
                <th scope="col" className="px-4 py-3 font-bold text-foreground">
                  Month
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-right font-bold text-foreground"
                >
                  Median price (SGD)
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-right font-bold text-foreground"
                >
                  Transactions
                </th>
              </tr>
            </thead>
            <tbody>
              {series.points.map((point) => (
                <tr key={point.month} className="border-b border-border/60">
                  <th
                    scope="row"
                    className="px-4 py-2 text-left font-normal text-foreground"
                  >
                    {point.month}
                  </th>
                  <td
                    data-numeric
                    className="px-4 py-2 text-right text-foreground"
                  >
                    {formatTrendNumber(point.price)}
                  </td>
                  <td
                    data-numeric
                    className="px-4 py-2 text-right text-foreground"
                  >
                    {formatTrendNumber(point.volume)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
