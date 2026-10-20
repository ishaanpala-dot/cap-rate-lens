function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="font-display text-lg font-semibold">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-[var(--ink-soft)]">
        {children}
      </div>
    </section>
  );
}

function Pull({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-display border-l-2 pl-4 text-lg italic leading-snug text-[var(--ink)]" style={{ borderColor: "var(--accent)" }}>
      {children}
    </p>
  );
}

export default function CaseStudy() {
  return (
    <div className="max-w-[72ch]">
      <p className="text-xs font-semibold tracking-[0.1em] uppercase" style={{ color: "var(--accent)" }}>
        Case study
      </p>
      <h1 className="font-display mt-2 text-2xl font-semibold tracking-tight">
        Building Cap Rate Lens: decisions, dead ends, and honesty as a design constraint
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-[var(--ink-soft)]">
        This page is the behind-the-scenes version of the About page: not what the tool does,
        but why it's built the way it is, including the parts that didn't work.
      </p>

      <Section title="The brief">
        <p>
          I work as a junior analyst at Craigmoor Property, doing fund valuation, Excel
          modelling and portfolio data day to day. I wanted a public portfolio piece that
          demonstrated that same thinking, cap rate mechanics, leverage amplification,
          risk ranking, built from scratch on real data, not internal spreadsheets. The one
          hard constraint going in: nothing from Craigmoor's own work could touch this
          project. Every figure had to trace back to something anyone else could also go
          and find in a public ASX announcement.
        </p>
      </Section>

      <Section title="The data problem turned out to be the real project">
        <Pull>
          Reading an AI-generated search summary and reading the actual filing are not the
          same thing, and the gap between them is exactly where bad data gets into a tool
          like this.
        </Pull>
        <p>
          Early on, several funds' WACR and sector splits came back as "not reported"
          because I was working from web search summaries. When I went back and read the
          primary ASX PDF releases directly instead, most of that data was sitting right
          there, just not in a form a search snippet happened to surface. That became a
          hard rule for the rest of the build: fetch the actual filing, read it, cite the
          exact page or figure, never trust a summary of a summary. It's slower, but it's
          the difference between a tool that's honestly sourced and one that just looks
          like it is.
        </p>
        <p>
          That same honesty rule caught a mistake I made myself: I briefly added a
          placeholder WALE figure for one fund's sector breakdown that I hadn't actually
          verified. Caught it on review and pulled it back out rather than leaving a
          plausible-looking number with nothing behind it. A tool whose entire pitch is
          "every figure is sourced" can't have even one figure that isn't.
        </p>
      </Section>

      <Section title="Why the data pipeline is still manual">
        <p>
          The obvious next step was automating that extraction, fetch each fund's results
          PDF on a schedule instead of re-reading everything by hand every session. That
          turned into a real investigation, not a quick win: ASX's own announcements
          platform prohibits automated scraping under its terms of use, which rules out
          the most direct path entirely. Each fund's own investor-relations site would
          need separate automation, and when I actually tried it for Dexus (plain HTTP
          fetch, then a full headless-browser render), neither approach found the actual
          results PDF, it's served by a feed that isn't in the rendered page at all, most
          likely a third-party IR widget. Charter Hall's site blocks even a plain
          robots.txt fetch behind bot detection.
        </p>
        <p>
          The honest call was to stop, document exactly what was tried and why it didn't
          work, and move on rather than either faking a solution or quietly dropping it.
          That write-up lives in the repo (<code className="tabular text-xs">docs/phase1-pipeline-status.md</code>) specifically so it
          isn't lost or re-investigated from scratch later. Knowing when a "small
          automation task" is actually a multi-day reverse-engineering project, and being
          willing to say so instead of pretending otherwise, felt like as much a part of
          this project as any of the code.
        </p>
      </Section>

      <Section title="Replacing a guess with a real estimate">
        <p>
          The Monte Carlo simulation originally used a flat assumption, cap rate shifts
          drawn from a normal distribution with a fixed, picked-by-eye standard
          deviation. It worked, but it was asserting precision it didn't have. The fix
          wasn't more code, it was going back to data: the RBA already publishes the full
          daily history of the 10-year government bond yield, which this tool was already
          fetching live for the risk-premium chart. That's a genuine time series with
          enough observations to estimate real volatility from, unlike any individual
          fund's WACR, which only gets reported once or twice a year.
        </p>
        <p>
          So the simulation now uses the realised standard deviation of day-over-day bond
          yield moves, annualised the standard way, as a proxy for cap rate volatility.
          It's still a proxy, not the real thing, and the UI says so directly next to the
          number, along with the exact window and sample size it came from. That's the
          pattern I wanted this whole project to follow: when you can't get the real
          number, say so and show your substitute's limitations, don't quietly present an
          assumption as if it were a fact.
        </p>
      </Section>

      <Section title="Picking a visual direction, not defaulting to one">
        <p>
          The first instinct for a data tool like this is dark-mode dashboard, blue
          accents, Inter everywhere, the generic "AI-built SaaS" look. Instead of
          reaching for that by default, I built three working mockups side by side before
          touching the real app: an editorial direction (warm paper tones, a serif
          display face, a deep green accent), a terminal direction (black background,
          amber monospace, bracket notation), and a Swiss/grid direction (stark black and
          white, a single red accent, heavy rules). Comparing real screenshots of all
          three, rather than imagining them, made the choice obvious, the editorial
          direction read the most like something written by someone with a point of view
          about property, not generated by a template.
        </p>
      </Section>

      <Section title="What I'd do differently">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Start the data-sourcing honesty rule (read the primary filing, never trust a
            summary) from day one rather than discovering the need for it partway through.
          </li>
          <li>
            Scope the automated pipeline investigation with a fixed time budget up front,
            it would have saved re-deciding partway through whether to keep pushing on
            Dexus's missing feed.
          </li>
          <li>
            Source a second historical WACR snapshot per fund earlier, not just the
            latest one, so comparisons like the risk-premium chart (which needs at least
            two data points) work across more than a single fund from the start.
          </li>
        </ul>
      </Section>
    </div>
  );
}
