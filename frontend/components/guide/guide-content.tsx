"use client";

import Link from "next/link";
import { ArrowRight, Check, ChevronRight, X } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ---------- 1. How the platform works ----------
const FLOW = [
  {
    title: "Strategy",
    text: "A set of rules you define, for example 'buy when a fast average crosses above a slow one'. It watches one symbol on one timeframe.",
  },
  {
    title: "Signal",
    text: "When a candle closes and the rules match, the strategy raises a BUY or SELL signal. No match means no signal.",
  },
  {
    title: "Risk check",
    text: "Every order is checked against your risk limits (daily loss, position size, order value and more) and the kill switch. Failing a check rejects the order.",
  },
  {
    title: "Order",
    text: "If the checks pass, an order is created and sent for execution. You can follow it on the Orders page.",
  },
  {
    title: "Paper broker",
    text: "In PAPER mode a built-in simulator fills the order at the current price plus a little slippage. Nothing reaches a real broker.",
  },
  {
    title: "Position",
    text: "A filled order opens a position. Its stop loss and target are watched, and its open profit or loss updates as the price moves.",
  },
  {
    title: "Trade",
    text: "When the position is closed (by a signal, stop loss, target or by you) it becomes a completed trade, with charges applied.",
  },
  {
    title: "P&L",
    text: "Completed trades roll up into your profit and loss, win rate and equity curve on the Dashboard.",
  },
];

function HowItWorks() {
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        Every automated trade follows the same path. Knowing it makes it much easier to work out where something
        stopped, for example why an order never appeared.
      </p>
      <div
        className="flex flex-wrap items-center gap-x-1.5 gap-y-2 rounded-lg border bg-muted/30 p-3 text-sm font-medium"
        aria-label="Flow summary"
      >
        {FLOW.map((step, i) => (
          <span key={step.title} className="flex items-center gap-1.5">
            {step.title}
            {i < FLOW.length - 1 ? <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden /> : null}
          </span>
        ))}
      </div>
      <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {FLOW.map((step, i) => (
          <li key={step.title} className="rounded-lg border bg-card p-3">
            <p className="flex items-center gap-2 text-sm font-semibold">
              <span className="tabular flex size-5 items-center justify-center rounded-full bg-secondary text-xs">
                {i + 1}
              </span>
              {step.title}
            </p>
            <p className="mt-1.5 text-sm text-muted-foreground">{step.text}</p>
          </li>
        ))}
      </ol>
      <p className="text-sm text-muted-foreground">
        In SANDBOX or LIVE mode the &quot;Paper broker&quot; step is replaced by a real broker, and the platform only
        gets there when every live-trading safety switch is on.
      </p>
    </div>
  );
}

// ---------- 2. Recommended workflow ----------
const WORKFLOW = [
  {
    title: "Stay in paper mode first",
    text: "Paper mode uses simulated fills with no real money. Leave it that way for a long time.",
    href: "/settings",
    link: "See the current mode",
  },
  {
    title: "Set your risk limits",
    text: "Decide the most you are willing to lose per trade and per day before you build anything. Limits protect you from your own mistakes and from bugs.",
    href: "/risk",
    link: "Open Risk",
  },
  {
    title: "Build a strategy",
    text: "Start with a simple one and keep risk at 1% of capital or less per trade, with a stop loss on every trade.",
    href: "/strategies/new",
    link: "Create a strategy",
  },
  {
    title: "Backtest it with costs, on real data",
    text: "Replay it over history with brokerage, slippage and statutory charges switched on. Check that the data source is not 'simulated': synthetic data proves nothing.",
    href: "/backtesting",
    link: "Open Backtesting",
  },
  {
    title: "Run it in paper for weeks",
    text: "A few good days mean very little. Let it run through different market moods (calm, trending, choppy) and collect at least 30 trades.",
    href: "/strategies",
    link: "Open Strategies",
  },
  {
    title: "Review your trades",
    text: "Look at winners and losers, charges paid and why trades were stopped out. Compare the paper results with the backtest. Big gaps are a warning.",
    href: "/trades",
    link: "Open Trades",
  },
  {
    title: "Only then think about real money",
    text: "If, after weeks of honest paper results, you still want to go further, use the SANDBOX environment first, start very small, and understand you can lose all of it.",
    href: "/brokers",
    link: "See broker safety checks",
  },
];

function Workflow() {
  return (
    <ol className="grid gap-3">
      {WORKFLOW.map((step, i) => (
        <li key={step.title} className="flex gap-3 rounded-lg border bg-card p-3 sm:p-4">
          <span className="tabular flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-semibold">
            {i + 1}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">{step.title}</p>
            <p className="mt-0.5 text-sm text-muted-foreground">{step.text}</p>
            <Link
              href={step.href}
              className={cn(buttonVariants({ variant: "link", size: "sm" }), "mt-1 h-auto p-0 text-xs")}
            >
              {step.link} <ChevronRight />
            </Link>
          </div>
        </li>
      ))}
    </ol>
  );
}

// ---------- 3. Do and don't ----------
const DOS = [
  {
    title: "Risk 1% of capital or less on each trade",
    text: "A run of ten losses in a row happens to almost every strategy. At 1% per trade that costs you roughly a tenth of your capital; at 10% per trade it costs roughly two-thirds.",
  },
  {
    title: "Always keep a stop loss",
    text: "A stop loss decides in advance how much a trade may lose. Without one, a single bad move can undo weeks of gains.",
  },
  {
    title: "Wait for 30 or more trades before drawing conclusions",
    text: "With only a handful of trades, luck looks exactly like skill. Fewer than 30 trades tells you very little.",
  },
  {
    title: "Watch costs, especially on 1-minute timeframes",
    text: "Brokerage, STT and other charges are paid on every trade. Fast strategies trade a lot, so costs can turn a small profit into a loss.",
  },
  {
    title: "Change one parameter at a time",
    text: "If you change three things and results improve, you will not know which change helped. Change one, test, then decide.",
  },
];
const DONTS = [
  {
    title: "Do not trust backtests run on synthetic data",
    text: "When the data source says 'simulated', the prices are generated, not real. Such a backtest only shows that the software works.",
  },
  {
    title: "Never disable or bypass the kill switch and safety limits",
    text: "They exist for the day something goes wrong. Do not raise a limit only to push a rejected order through: first find out why it was rejected.",
  },
  {
    title: "Do not chase losses",
    text: "Increasing size or switching rules to win back a loss is how small losses become large ones. Stick to your plan or stop the strategy.",
  },
  {
    title: "Do not treat a good backtest as a promise",
    text: "The past does not repeat on cue. A strategy fitted too closely to old data often fails on new data.",
  },
  {
    title: "Do not go live because paper trading felt easy",
    text: "Real money brings slippage, missed fills and stress. Paper results are usually somewhat better than reality.",
  },
];

function ListCard({
  title,
  items,
  kind,
}: {
  title: string;
  items: { title: string; text: string }[];
  kind: "do" | "dont";
}) {
  const Icon = kind === "do" ? Check : X;
  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className={cn("mb-3 text-sm font-semibold", kind === "do" ? "text-profit" : "text-loss")}>{title}</h3>
      <ul className="grid gap-3">
        {items.map((item) => (
          <li key={item.title} className="flex gap-2.5">
            <Icon
              className={cn("mt-0.5 size-4 shrink-0", kind === "do" ? "text-profit" : "text-loss")}
              aria-label={kind === "do" ? "Do" : "Don't"}
            />
            <div className="text-sm">
              <p className="font-medium">{item.title}</p>
              <p className="text-muted-foreground">{item.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DoAndDont() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ListCard title="Do" items={DOS} kind="do" />
      <ListCard title="Don't" items={DONTS} kind="dont" />
    </div>
  );
}

// ---------- 4. Glossary ----------
const GLOSSARY = [
  {
    term: "Signal",
    text: "A BUY or SELL suggestion raised by a strategy when its rules match on a closed candle. A signal is not an order: it still has to pass the risk checks.",
  },
  {
    term: "Stop loss",
    text: "A price at which a losing trade is closed automatically to cap the loss. Example: buy at ₹100 with a 1% stop loss and the trade exits near ₹99.",
  },
  {
    term: "Target",
    text: "A price at which a winning trade is closed automatically to lock in the profit. Example: a 2% target on a ₹100 entry exits near ₹102.",
  },
  {
    term: "Reward:risk",
    text: "How much you aim to win compared with how much you risk. A 2% target with a 1% stop loss is 2:1. Higher is better, but a high ratio is often hit less often.",
  },
  {
    term: "Position sizing",
    text: "Deciding how many shares to trade so that a stopped-out trade loses only the amount you chose to risk (for example 1% of capital), instead of a fixed number of shares.",
  },
  {
    term: "Drawdown",
    text: "The fall from a peak in your account value to the following low. A 10% drawdown means you are 10% below your best point. Ask yourself whether you could sit through it.",
  },
  {
    term: "Profit factor",
    text: "Total profit from winning trades divided by total loss from losing trades. Above 1 means winners outweigh losers; around 1 means you are just breaking even before costs.",
  },
  {
    term: "Slippage",
    text: "The gap between the price you expected and the price you actually got. It is usually small but it costs you on every trade, more so in fast or thinly traded stocks.",
  },
  {
    term: "Brokerage and STT",
    text: "Costs on each trade. Brokerage is what the broker charges; STT is the Securities Transaction Tax. Exchange charges, SEBI fees, stamp duty and GST are added on top. Backtests here can include all of them.",
  },
  {
    term: "Paper, sandbox and live",
    text: "Paper: simulated trading inside this platform, no broker involved. Sandbox: a broker's test environment with pretend money. Live: real orders and real money.",
  },
  {
    term: "Kill switch",
    text: "An emergency stop. It stops all strategies, blocks new orders and cancels pending orders. Open positions stay open unless you enabled closing them in the risk settings.",
  },
];

function Glossary() {
  return (
    <dl className="grid gap-3 md:grid-cols-2">
      {GLOSSARY.map((g) => (
        <div key={g.term} className="rounded-lg border bg-card p-3">
          <dt className="text-sm font-semibold">{g.term}</dt>
          <dd className="mt-0.5 text-sm text-muted-foreground">{g.text}</dd>
        </div>
      ))}
    </dl>
  );
}

// ---------- 5. FAQ ----------
const FAQ: { q: string; a: React.ReactNode }[] = [
  {
    q: "Why did my order get rejected?",
    a: (
      <>
        <p>
          Almost always a risk limit or the kill switch. The common ones are: the maximum daily loss, the maximum
          order value, the maximum position size, too many open positions or trades today, or a losing streak.
        </p>
        <p>
          Open the order on the <Link className="underline underline-offset-4" href="/orders">Orders</Link> page for
          its status message, then look in <Link className="underline underline-offset-4" href="/events">Logs</Link>{" "}
          for a <code className="font-mono text-xs">risk_check_failed</code> event with the exact reason. Change a
          limit on the <Link className="underline underline-offset-4" href="/risk">Risk</Link> page only if you
          understand why it blocked you.
        </p>
      </>
    ),
  },
  {
    q: "Why have I got no signals yet?",
    a: (
      <>
        <p>
          A strategy only looks at a candle when it closes, and it only raises a signal when its rule actually
          matches, for example when two averages cross. On a 5-minute timeframe that check happens once every five
          minutes, and a crossover may take hours or days to appear.
        </p>
        <p>
          With real market data nothing happens while the market is closed (NSE trades 9:15 to 15:30 IST on
          weekdays). Check that the strategy shows RUNNING and look at its &quot;last evaluated&quot; time on the
          Strategies page. No signals is normal, not a fault.
        </p>
      </>
    ),
  },
  {
    q: "What does HALTED mean?",
    a: (
      <p>
        The kill switch is on. All strategies were stopped, new orders are blocked and pending orders were
        cancelled. Open positions stay open unless you enabled closing them in the risk settings. To carry on, use
        &quot;Resume trading&quot; in the red banner. Resuming does not restart strategies: start each one again
        yourself.
      </p>
    ),
  },
  {
    q: "How do I add another user?",
    a: (
      <>
        <p>
          An admin sets <code className="font-mono text-xs">ALLOW_REGISTRATION=true</code> in the{" "}
          <code className="font-mono text-xs">.env</code> file and applies it with{" "}
          <code className="font-mono text-xs">docker compose up -d backend</code> (a plain restart does not re-read{" "}
          <code className="font-mono text-xs">.env</code>). The new person then registers from the login page.
          Afterwards the admin should set it back to <code className="font-mono text-xs">false</code> and run the same
          command again, so that strangers cannot sign up.
        </p>
        <p>
          Important: all users currently share the same strategies, orders, positions and data. There are no
          separate accounts of trades per user, so anyone with a login can see and change everything.
        </p>
      </>
    ),
  },
  {
    q: "Is it safe?",
    a: (
      <>
        <p>
          Paper mode never reaches a real broker: it is a simulation inside the platform. Live trading needs four
          separate switches to be on at the same time, and you can see each one, with its current state, under
          &quot;Live trading guards&quot; on the{" "}
          <Link className="underline underline-offset-4" href="/brokers">Brokers</Link> page. Broker passwords and
          keys are never entered or shown in this app.
        </p>
        <p>
          Safe does not mean profitable. Even in paper mode, results can be better than real trading would be.
        </p>
      </>
    ),
  },
  {
    q: "If a backtest looks great, will the strategy make money?",
    a: (
      <p>
        No. A backtest only shows what would have happened in the past, and markets change. Treat it as a way to
        weed out bad ideas, not as proof a good one will work. Nothing in this platform is investment advice.
      </p>
    ),
  },
];

function Faq() {
  return (
    <div className="grid gap-2">
      {FAQ.map((item) => (
        <details key={item.q} className="group rounded-lg border bg-card">
          <summary className="flex cursor-pointer list-none items-center gap-2 p-3 text-sm font-medium select-none marker:hidden [&::-webkit-details-marker]:hidden">
            <ChevronRight className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90" aria-hidden />
            {item.q}
          </summary>
          <div className="grid gap-2 border-t p-3 pl-9 text-sm text-muted-foreground">{item.a}</div>
        </details>
      ))}
    </div>
  );
}

// ---------- Tabs ----------
const TABS = [
  { value: "how", label: "How it works", body: <HowItWorks /> },
  { value: "workflow", label: "Recommended workflow", body: <Workflow /> },
  { value: "practice", label: "Do and don't", body: <DoAndDont /> },
  { value: "glossary", label: "Glossary", body: <Glossary /> },
  { value: "faq", label: "FAQ", body: <Faq /> },
];

export function GuideContent() {
  return (
    <Tabs defaultValue="how" className="gap-4">
      <div className="overflow-x-auto pb-1">
        <TabsList className="w-max">
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value} className="px-3">
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
      {TABS.map((t) => (
        <TabsContent key={t.value} value={t.value}>
          {t.body}
        </TabsContent>
      ))}
    </Tabs>
  );
}
