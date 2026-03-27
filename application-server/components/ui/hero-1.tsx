"use client";

import * as React from "react";
import { ArrowRight, CheckCircle2, Loader2, MapPin, Paperclip, SendHorizonal, Sparkles, Tag } from "lucide-react";

type UiState = "idle" | "input" | "uploading" | "analyzing" | "success" | "error" | "empty";

type AnalysisRequest = {
  query: string;
  file: File | null;
};

type ProductComparison = {
  name: string;
  recommendedPrice: string;
  comparePrice: string;
  status: "deal" | "normal" | "higher";
};

type AlternativeMarket = {
  name: string;
  note: string;
  savingsDelta: string;
};

type AnalysisResult = {
  market: string;
  estimatedSavings: string;
  distance: string;
  relevance: string;
  reason: string;
  ctaLabel: string;
  priceAdvantage: string[];
  listInsights: string[];
  alternatives: AlternativeMarket[];
  products: ProductComparison[];
};

type InputSectionProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => Promise<void>;
  onUploadClick: () => void;
  onQuickAction: (value: string) => Promise<void>;
  busy: boolean;
  selectedFile: File | null;
};

type AnalysisStepperProps = {
  activeStep: number;
  visible: boolean;
};

type RecommendationHeroProps = {
  result: AnalysisResult;
  onPrimaryAction: () => void;
};

type ReasonCardsProps = {
  result: AnalysisResult;
};

type ProductComparisonListProps = {
  products: ProductComparison[];
};

const QUICK_ACTIONS = [
  "Weekly groceries for 2 adults",
  "Best offers for milk, eggs, and bread",
  "Analyze shopping list from screenshot",
];

const ANALYSIS_STEPS = [
  "Reading shopping list",
  "Recognizing products",
  "Comparing supermarket offers",
  "Calculating best option",
];

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const analyzeShoppingDecision = async ({ query, file }: AnalysisRequest): Promise<AnalysisResult> => {
  // Replace with real API call after backend integration.
  await wait(1200);
  const normalized = query.toLowerCase();

  if (!query.trim() && !file) {
    throw new Error("EMPTY_INPUT");
  }
  if (normalized.includes("error")) {
    throw new Error("ANALYSIS_FAILED");
  }

  if (normalized.includes("pasta")) {
    return {
      market: "Lidl",
      estimatedSavings: "EUR 6.40",
      distance: "1.2 km",
      relevance: "89%",
      reason: "Most pasta-related products are currently on promotion.",
      ctaLabel: "Open Lidl deal list",
      priceAdvantage: [
        "Total cart is 14% cheaper than average nearby options.",
        "3 of 5 requested items are currently on promotion.",
      ],
      listInsights: [
        "Tomato products appear in multiple discount bundles.",
        "Best value found for pasta and parmesan combinations.",
      ],
      alternatives: [
        { name: "Aldi", note: "Close second option", savingsDelta: "- EUR 1.10" },
        { name: "Rewe", note: "Higher convenience, fewer deals", savingsDelta: "- EUR 2.30" },
      ],
      products: [
        { name: "Pasta", recommendedPrice: "EUR 0.79", comparePrice: "EUR 1.29", status: "deal" },
        { name: "Tomatoes", recommendedPrice: "EUR 1.49", comparePrice: "EUR 1.69", status: "deal" },
        { name: "Parmesan", recommendedPrice: "EUR 2.89", comparePrice: "EUR 3.19", status: "deal" },
      ],
    };
  }

  if (normalized.includes("week") || normalized.includes("weekly")) {
    return {
      market: "Kaufland",
      estimatedSavings: "EUR 9.10",
      distance: "2.0 km",
      relevance: "93%",
      reason: "Best full-basket pricing for weekly essentials.",
      ctaLabel: "Use Kaufland recommendation",
      priceAdvantage: [
        "Basket total is 18% below nearby median price.",
        "High offer coverage for dairy, bakery, and produce.",
      ],
      listInsights: [
        "Large-pack products improve per-unit costs.",
        "Discount overlap is strongest in breakfast products.",
      ],
      alternatives: [
        { name: "Lidl", note: "Similar basket, slightly higher total", savingsDelta: "- EUR 1.80" },
        { name: "Edeka", note: "Good quality, weaker discount coverage", savingsDelta: "- EUR 4.40" },
      ],
      products: [
        { name: "Milk (1L)", recommendedPrice: "EUR 0.95", comparePrice: "EUR 1.19", status: "deal" },
        { name: "Eggs (10)", recommendedPrice: "EUR 2.29", comparePrice: "EUR 2.69", status: "deal" },
        { name: "Bread", recommendedPrice: "EUR 1.39", comparePrice: "EUR 1.39", status: "normal" },
        { name: "Apples (1kg)", recommendedPrice: "EUR 2.49", comparePrice: "EUR 2.29", status: "higher" },
      ],
    };
  }

  return {
    market: "Rewe",
    estimatedSavings: "EUR 4.20",
    distance: "0.8 km",
    relevance: "84%",
    reason: "Best match between your list and active offers in your area.",
    ctaLabel: "Review Rewe recommendation",
    priceAdvantage: [
      "Balanced total price with strong offer coverage.",
      "Good availability for all recognized products.",
    ],
    listInsights: [
      "2 products were mapped to comparable alternatives.",
      "One premium brand can be swapped for a cheaper equivalent.",
    ],
    alternatives: [
      { name: "Aldi", note: "Cheaper on selected staples", savingsDelta: "- EUR 1.00" },
      { name: "Kaufland", note: "More bulk offers", savingsDelta: "- EUR 0.70" },
    ],
    products: [
      { name: "Milk (1L)", recommendedPrice: "EUR 1.05", comparePrice: "EUR 1.19", status: "deal" },
      { name: "Eggs (10)", recommendedPrice: "EUR 2.45", comparePrice: "EUR 2.39", status: "higher" },
      { name: "Wholegrain Bread", recommendedPrice: "EUR 1.59", comparePrice: "EUR 1.69", status: "deal" },
    ],
  };
};

function Header({ isLoggedIn, onToggleLogin, mode }: { isLoggedIn: boolean; onToggleLogin: () => void; mode: UiState }) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-indigo-600">
            <Sparkles className="h-4 w-4 text-white" />
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">SmartCart Assist</p>
            <p className="text-xs text-slate-500">Supermarket decision engine</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">{mode}</span>
          <button
            type="button"
            onClick={onToggleLogin}
            className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
          >
            {isLoggedIn ? "Account" : "Login"}
          </button>
        </div>
      </div>
    </header>
  );
}

function InputSection({
  value,
  onChange,
  onSubmit,
  onUploadClick,
  onQuickAction,
  busy,
  selectedFile,
}: InputSectionProps) {
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit();
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
      <h1 className="text-lg font-semibold text-slate-900 sm:text-xl">Was moechtest du einkaufen?</h1>
      <p className="mt-1 text-sm text-slate-600">Type your list or upload a screenshot. Press Enter to analyze.</p>

      <form onSubmit={handleSubmit} className="mt-4">
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-2">
          <button
            type="button"
            onClick={onUploadClick}
            className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 transition hover:bg-slate-100"
            aria-label="Upload file"
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <input
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="e.g. milk, eggs, bread, tomatoes"
            className="flex-1 bg-transparent px-1 text-sm text-slate-900 outline-none placeholder:text-slate-400"
          />
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-300"
          >
            <SendHorizonal className="h-4 w-4" />
            Analyze
          </button>
        </div>
      </form>

      {selectedFile ? <p className="mt-2 text-xs text-slate-500">Uploaded: {selectedFile.name}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action}
            type="button"
            onClick={() => onQuickAction(action)}
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
          >
            {action}
          </button>
        ))}
      </div>
    </section>
  );
}

function AnalysisStepper({ activeStep, visible }: AnalysisStepperProps) {
  if (!visible) return null;
  return (
    <section className="rounded-2xl border border-indigo-100 bg-indigo-50 p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-indigo-700">
        <Loader2 className="h-4 w-4 animate-spin" />
        Analyzing your basket
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {ANALYSIS_STEPS.map((step, index) => {
          const isDone = index < activeStep;
          const isCurrent = index === activeStep;
          return (
            <div
              key={step}
              className={`rounded-xl border px-3 py-2 text-sm ${
                isDone
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                  : isCurrent
                    ? "border-indigo-200 bg-white text-indigo-800"
                    : "border-slate-200 bg-white text-slate-500"
              }`}
            >
              {step}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RecommendationHero({ result, onPrimaryAction }: RecommendationHeroProps) {
  return (
    <section className="rounded-2xl border border-emerald-200 bg-gradient-to-b from-emerald-50 to-white p-5 shadow-sm sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Recommended supermarket</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{result.market}</h2>
          <p className="mt-1 text-sm text-slate-700">{result.reason}</p>
        </div>
        <button
          type="button"
          onClick={onPrimaryAction}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          {result.ctaLabel}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <div className="rounded-xl border border-emerald-100 bg-white p-3">
          <p className="text-xs text-slate-500">Estimated savings</p>
          <p className="text-lg font-semibold text-emerald-700">{result.estimatedSavings}</p>
        </div>
        <div className="rounded-xl border border-emerald-100 bg-white p-3">
          <p className="text-xs text-slate-500">Distance</p>
          <p className="inline-flex items-center gap-1 text-lg font-semibold text-slate-900">
            <MapPin className="h-4 w-4 text-slate-500" />
            {result.distance}
          </p>
        </div>
        <div className="rounded-xl border border-emerald-100 bg-white p-3">
          <p className="text-xs text-slate-500">Relevance</p>
          <p className="text-lg font-semibold text-slate-900">{result.relevance}</p>
        </div>
      </div>
    </section>
  );
}

function ReasonCards({ result }: ReasonCardsProps) {
  return (
    <section className="grid gap-3 sm:grid-cols-2">
      <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Price advantage</h3>
        <ul className="mt-2 space-y-1.5">
          {result.priceAdvantage.map((point) => (
            <li key={point} className="flex items-start gap-2 text-sm text-slate-700">
              <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </article>
      <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Shopping list insights</h3>
        <ul className="mt-2 space-y-1.5">
          {result.listInsights.map((point) => (
            <li key={point} className="flex items-start gap-2 text-sm text-slate-700">
              <Tag className="mt-0.5 h-4 w-4 text-indigo-500" />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </article>
      <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:col-span-2">
        <h3 className="text-sm font-semibold text-slate-900">Alternatives</h3>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {result.alternatives.map((alternative) => (
            <div key={alternative.name} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="text-sm font-semibold text-slate-900">{alternative.name}</p>
              <p className="text-xs text-slate-600">{alternative.note}</p>
              <p className="mt-1 text-sm font-medium text-slate-800">{alternative.savingsDelta}</p>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function ProductComparisonList({ products }: ProductComparisonListProps) {
  const badgeClass: Record<ProductComparison["status"], string> = {
    deal: "bg-emerald-100 text-emerald-700",
    normal: "bg-slate-100 text-slate-700",
    higher: "bg-amber-100 text-amber-700",
  };
  const badgeLabel: Record<ProductComparison["status"], string> = {
    deal: "on deal",
    normal: "normal",
    higher: "higher",
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Product comparison</h3>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 pr-3 font-medium">Product</th>
              <th className="py-2 pr-3 font-medium">Recommended market</th>
              <th className="py-2 pr-3 font-medium">Comparison price</th>
              <th className="py-2 pr-0 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.name} className="border-b border-slate-100 text-sm text-slate-800 last:border-b-0">
                <td className="py-3 pr-3 font-medium">{product.name}</td>
                <td className="py-3 pr-3">{product.recommendedPrice}</td>
                <td className="py-3 pr-3 text-slate-600">{product.comparePrice}</td>
                <td className="py-3 pr-0">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClass[product.status]}`}>
                    {badgeLabel[product.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function EmptyState() {
  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
      Add a shopping list or upload a screenshot to start the recommendation.
    </section>
  );
}

function ErrorState({ onRetry }: { onRetry: () => Promise<void> }) {
  return (
    <section className="rounded-2xl border border-red-200 bg-red-50 p-4">
      <p className="text-sm font-medium text-red-700">Analysis failed. Please try again.</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-100"
      >
        Retry analysis
      </button>
    </section>
  );
}

const Hero1 = () => {
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const [uiState, setUiState] = React.useState<UiState>("idle");
  const [isLoggedIn, setIsLoggedIn] = React.useState(false);
  const [inputValue, setInputValue] = React.useState("");
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [result, setResult] = React.useState<AnalysisResult | null>(null);
  const [analysisStep, setAnalysisStep] = React.useState(0);
  const [actionNotice, setActionNotice] = React.useState<string | null>(null);

  const runAnalysis = React.useCallback(
    async (presetValue?: string) => {
      const nextValue = (presetValue ?? inputValue).trim();
      setActionNotice(null);
      setResult(null);

      if (!nextValue && !selectedFile) {
        setUiState("empty");
        return;
      }

      setUiState("analyzing");
      setAnalysisStep(0);

      for (let index = 0; index < ANALYSIS_STEPS.length; index += 1) {
        setAnalysisStep(index);
        await wait(320);
      }

      try {
        const nextResult = await analyzeShoppingDecision({ query: nextValue, file: selectedFile });
        setResult(nextResult);
        setUiState("success");
      } catch (error) {
        if (error instanceof Error && error.message === "EMPTY_INPUT") {
          setUiState("empty");
          return;
        }
        setUiState("error");
      }
    },
    [inputValue, selectedFile],
  );

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (!file) return;
    setSelectedFile(file);
    setUiState("uploading");
    await wait(450);
    setUiState(inputValue.trim() ? "input" : "idle");
  };

  const handleInputChange = (value: string) => {
    setInputValue(value);
    setUiState(value.trim() ? "input" : "idle");
  };

  const handlePrimaryAction = () => {
    if (!result) return;
    setActionNotice(`Primary action triggered: ${result.market}`);
  };

  const busy = uiState === "analyzing" || uiState === "uploading";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header isLoggedIn={isLoggedIn} onToggleLogin={() => setIsLoggedIn((prev) => !prev)} mode={uiState} />

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-5 sm:px-6 sm:py-6">
        <InputSection
          value={inputValue}
          onChange={handleInputChange}
          onSubmit={runAnalysis}
          onUploadClick={handleUploadClick}
          onQuickAction={runAnalysis}
          busy={busy}
          selectedFile={selectedFile}
        />
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/*,.pdf,.txt"
          onChange={handleFileChange}
        />

        <AnalysisStepper activeStep={analysisStep} visible={uiState === "analyzing"} />
        {uiState === "empty" ? <EmptyState /> : null}
        {uiState === "error" ? <ErrorState onRetry={runAnalysis} /> : null}

        {result ? (
          <div className="grid gap-4">
            <RecommendationHero result={result} onPrimaryAction={handlePrimaryAction} />
            <ReasonCards result={result} />
            <ProductComparisonList products={result.products} />
          </div>
        ) : null}

        {actionNotice ? (
          <div className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700">{actionNotice}</div>
        ) : null}
      </main>
    </div>
  );
};

export { Hero1 };
