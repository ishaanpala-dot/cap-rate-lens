function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="font-display text-lg font-semibold">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
        {children}
      </div>
    </section>
  );
}

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <div className="tabular rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3 text-xs text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300">
      {children}
    </div>
  );
}

export default function About() {
  return (
    <div className="max-w-[72ch]">
      <Section title="Why this exists">
        <p>
          I'm an analyst (Craigmoor Property) working on property fund valuation, Excel
          modelling and portfolio data day to day. This tool takes that same kind of
          work, cap rate mechanics, NAV sensitivity, sector and leverage risk, and turns
          it into something public and interactive, built on real ASX-listed fund data
          instead of internal spreadsheets.
        </p>
        <p>
          It's a demonstration of how I think about property valuation and build data
          products, not a replacement for institutional tools like Bloomberg or
          CoreLogic. The data is manually sourced from public quarterly and half-year
          results for now, which is an honest limitation covered below.
        </p>
      </Section>

      <Section title="What it does">
        <p>
          Tracks eight major ASX-listed property trusts (Dexus, GPT, Charter Hall Long
          WALE REIT, Mirvac, Stockland, Goodman, Scentre, Vicinity) and lets you:
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>See each fund's NTA per security, WACR, gearing and WALE at a glance</li>
          <li>Move a fund's cap rate on a slider and watch its NTA respond in real time</li>
          <li>Compare all eight funds side by side, sorted by any metric</li>
          <li>See each fund's sector split (office / retail / industrial / logistics)</li>
          <li>Track a fund's cap rate against the 10-year government bond yield over time</li>
          <li>Rank funds by how much leverage amplifies their cap rate risk</li>
          <li>See a probability range for NTA outcomes, not just one point estimate</li>
        </ul>
      </Section>

      <Section title="The core mechanic: cap rate sensitivity">
        <p>
          Commercial property valuation rests on one identity: value equals net operating
          income divided by the cap rate. Holding income fixed, if the cap rate moves,
          the asset's value moves inversely.
        </p>
        <Formula>Asset value = Net operating income / Cap rate</Formula>
        <p>
          The part that actually matters for an equity investor is what happens after
          debt. A fund's balance sheet is assets minus debt equals NTA (net tangible
          assets, the equity). Debt doesn't move when property values move in the short
          run, so a swing in asset value flows entirely into the much smaller equity
          base. That's leverage amplification, and it's why a 1% cap rate move can shift
          NTA by 15 to 25%, not 1%.
        </p>
        <Formula>
          Assets = NTA / (1 - gearing)
          <br />
          Debt = Assets - NTA
          <br />
          New assets = Assets x (old cap rate / new cap rate)
          <br />
          New NTA = New assets - Debt
        </Formula>
        <p>
          This is exactly the formula behind the cap rate slider on the Fund detail tab,
          and the leverage ranking on the Market comparison tab is just this same
          calculation run for a standard +1% cap rate shock, across every fund that
          reports both WACR and gearing.
        </p>
      </Section>

      <Section title="Cap rate risk premium">
        <p>
          A cap rate on its own doesn't say whether property is cheap or expensive,
          it has to be compared against the risk-free alternative. The convention
          institutional property investors use is the cap rate risk premium: WACR minus
          the 10-year government bond yield.
        </p>
        <Formula>Risk premium = WACR - 10-year government bond yield</Formula>
        <p>
          A wide premium suggests property is pricing in a lot of extra risk versus
          bonds, a historically unusual premium (wide or narrow) is often a signal cap
          rates are due to move. The chart on the Fund detail tab plots a fund's WACR
          against the bond yield over the periods it has data for, with the gap between
          the lines shaded to make the premium visible at a glance, rather than making
          someone subtract two numbers in their head.
        </p>
      </Section>

      <Section title="Simulated NTA range (Monte Carlo)">
        <p>
          A single slider value answers "what if the cap rate moves to exactly X", which
          is useful but implies false precision, nobody knows the exact future cap rate.
          The simulation instead draws 5,000 random cap rate shifts from a normal
          distribution centred on the fund's current WACR, runs each one through the
          same valuation formula above, and reports the 10th, 25th, 50th, 75th and 90th
          percentile outcomes.
        </p>
        <p>
          The standard deviation used for that distribution (0.5 percentage points by
          default) is a simplifying assumption, not a number fitted to historical
          volatility, there isn't enough public quarterly history yet to estimate that
          properly. That's stated directly in the tool rather than presented as more
          rigorous than it is.
        </p>
      </Section>

      <Section title="Why these specific visuals">
        <p>
          Every chart choice here is trying to match the shape of the underlying
          question, not just "add a chart":
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <span className="font-medium text-zinc-900 dark:text-zinc-100">Line chart with shaded area</span> for the risk premium, because the
            question is about the gap between two series over time, not either series alone
          </li>
          <li>
            <span className="font-medium text-zinc-900 dark:text-zinc-100">Donut chart</span> for sector exposure, because the question is
            "what share of the whole portfolio", a part-to-whole comparison a donut reads
            faster than a bar
          </li>
          <li>
            <span className="font-medium text-zinc-900 dark:text-zinc-100">Horizontal bar chart</span> for leverage ranking, because the
            question is a simple ordered comparison across funds, bars make the ranking
            and magnitude both obvious at once
          </li>
          <li>
            <span className="font-medium text-zinc-900 dark:text-zinc-100">Fan / range chart</span> for the Monte Carlo result, to make a
            distribution visually distinct from the single point estimate above it
          </li>
          <li>
            <span className="font-medium text-zinc-900 dark:text-zinc-100">Monospace numerals</span> everywhere a figure appears, so
            columns of numbers align and read like financial data, not prose
          </li>
        </ul>
      </Section>

      <Section title="Data sourcing and honesty">
        <p>
          Every figure is sourced from a fund's own public ASX announcements (quarterly
          updates, half-year and full-year results), cited inline wherever it's shown.
          Nothing here is estimated or invented to fill a gap. Where a figure the model
          needs (WACR for six of the eight funds, sector splits for six of the eight)
          hasn't been sourced yet, the tool shows "n/a" with a note explaining that
          honestly: not every gap has been confirmed as the fund simply not disclosing
          it, some are genuinely just not extracted yet. The two are shown the same way
          for now, because claiming to know the difference without having checked would
          be its own kind of dishonesty.
        </p>
        <p>
          The sector exposure percentages for Dexus and GPT are calculated from dollar
          or income figures in their results releases, since neither fund publishes an
          official percentage table, that calculation and its source are stated directly
          under each chart.
        </p>
        <p>
          The 10-year government bond yield, used in the risk premium chart, is the one
          figure on this page that's fully automated: it's fetched live from the RBA's
          own daily statistical table (series FCMYGBAG10D), cached for up to 12 hours,
          with no manual step involved. Every other figure here is still sourced by
          hand, that gap is exactly what the planned extraction pipeline is for.
        </p>
      </Section>

      <Section title="What's next">
        <p>
          The honest gap right now is breadth and freshness: six of eight funds are
          missing WACR because it takes a line-by-line read of each fund's full results
          PDF to extract, work that's currently manual. The planned fix is an automated
          extraction pipeline (structured parsing of each fund's quarterly PDF) so the
          dataset can be refreshed every reporting season without someone re-reading
          every report by hand. That pipeline is scaffolded but not yet built.
        </p>
      </Section>
    </div>
  );
}
