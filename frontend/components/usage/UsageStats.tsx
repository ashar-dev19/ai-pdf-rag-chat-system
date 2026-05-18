import { type ModelUsage } from "@/lib/api";

// ── Model display config ────────────────────────────────────────────────────

const MODEL_LABELS: Record<string, string> = {
  "gemini-2.5-flash": "Gemini 2.5 Flash",
  "claude-haiku-4-5-20251001": "Claude Haiku",
  "claude-sonnet-4-6": "Claude Sonnet",
};

// Pricing per 1M tokens in USD (approximate — verify at console.anthropic.com)
const MODEL_PRICING: Record<string, { input: number; output: number }> = {
  "claude-haiku-4-5-20251001": { input: 0.80, output: 4.00 },
  "claude-sonnet-4-6": { input: 3.00, output: 15.00 },
};

// Free-tier limits
const GEMINI_DAILY_LIMIT = 20;        // requests/day — gemini-2.5-flash free tier
const GEMINI_RPM_LIMIT = 15;          // requests/minute — gemini-2.5-flash free tier
const ANTHROPIC_BUDGET_USD = 5.00;   // $5 free credit
const VOYAGE_BUDGET_USD = 10.00;     // $10 free credit on signup

// ── Helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number) {
  return n.toLocaleString();
}

function estimateCost(model: string, inputTokens: number, outputTokens: number): number {
  const p = MODEL_PRICING[model];
  if (!p) return 0;
  return (inputTokens / 1_000_000) * p.input + (outputTokens / 1_000_000) * p.output;
}

function ProgressBar({ pct, color }: { pct: number; color: string }) {
  const clamped = Math.min(Math.max(pct, 0), 100);
  const warn = clamped >= 80;
  return (
    <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1.5">
      <div
        className={`h-1.5 rounded-full transition-all ${warn ? "bg-red-400" : color}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

// Voyage AI pricing per 1M tokens
const VOYAGE_PRICE_PER_M = 0.12; // voyage-3, approx — verify at dash.voyageai.com

// ── Card variants ────────────────────────────────────────────────────────────

function GeminiCard({ m }: { m: ModelUsage }) {
  const dayPct = (m.today_requests / GEMINI_DAILY_LIMIT) * 100;
  const rpmPct = (m.last_minute_requests / GEMINI_RPM_LIMIT) * 100;
  const dayWarn = dayPct >= 80;
  const rpmWarn = rpmPct >= 80;
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 min-w-[200px]">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-700">{MODEL_LABELS[m.model] ?? m.model}</p>
        <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-medium">Free tier</span>
      </div>

      <p className="text-xs text-gray-500 mt-1">
        {fmt(m.total_input_tokens)} in · {fmt(m.total_output_tokens)} out
      </p>

      <div className="mt-1.5 flex flex-col gap-2">
        <div>
          <div className="flex justify-between items-center">
            <p className="text-xs text-gray-500">Daily (RPD)</p>
            <p className={`text-xs font-medium ${dayWarn ? "text-red-500" : "text-gray-700"}`}>
              {m.today_requests} / {GEMINI_DAILY_LIMIT}
            </p>
          </div>
          <ProgressBar pct={dayPct} color="bg-blue-400" />
          {dayWarn && <p className="text-[10px] text-red-500 mt-0.5">Approaching daily limit · resets at midnight UTC</p>}
        </div>

        <div>
          <div className="flex justify-between items-center">
            <p className="text-xs text-gray-500">Per minute (RPM)</p>
            <p className={`text-xs font-medium ${rpmWarn ? "text-red-500" : "text-gray-700"}`}>
              {m.last_minute_requests} / {GEMINI_RPM_LIMIT}
            </p>
          </div>
          <ProgressBar pct={rpmPct} color="bg-blue-300" />
          {rpmWarn && <p className="text-[10px] text-red-500 mt-0.5">Slow down — rate limit imminent</p>}
        </div>
      </div>
    </div>
  );
}

function ClaudeCard({ m }: { m: ModelUsage }) {
  const cost = estimateCost(m.model, m.total_input_tokens, m.total_output_tokens);
  const pct = (cost / ANTHROPIC_BUDGET_USD) * 100;
  const remaining = Math.max(0, ANTHROPIC_BUDGET_USD - cost);
  const warn = pct >= 80;
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-purple-100 bg-purple-50 px-4 py-3 min-w-[180px]">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-purple-700">{MODEL_LABELS[m.model] ?? m.model}</p>
        <span className="text-[10px] bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded-full font-medium">$5 credit</span>
      </div>

      <p className="text-xs text-gray-500 mt-1">
        {fmt(m.total_input_tokens)} in · {fmt(m.total_output_tokens)} out
      </p>

      <div className="mt-1.5">
        <div className="flex justify-between items-center">
          <p className="text-xs text-gray-500">Budget used</p>
          <p className={`text-xs font-medium ${warn ? "text-red-500" : "text-gray-700"}`}>
            ${cost.toFixed(4)} / $5.00
          </p>
        </div>
        <ProgressBar pct={pct} color="bg-purple-400" />
        <p className={`text-[10px] mt-1 ${warn ? "text-red-500" : "text-gray-400"}`}>
          {warn ? "Low balance! " : ""}${remaining.toFixed(4)} remaining
        </p>
      </div>

      <p className="text-[10px] text-gray-400">
        Pricing: $0.80/1M in · $4.00/1M out (approx.)
      </p>
    </div>
  );
}

function VoyageCard({ m }: { m: ModelUsage }) {
  const cost = (m.total_input_tokens / 1_000_000) * VOYAGE_PRICE_PER_M;
  const pct = (cost / VOYAGE_BUDGET_USD) * 100;
  const remaining = Math.max(0, VOYAGE_BUDGET_USD - cost);
  const warn = pct >= 80;
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-orange-100 bg-orange-50 px-4 py-3 min-w-[180px]">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-orange-700">Voyage AI</p>
        <span className="text-[10px] bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded-full font-medium">$10 credit</span>
      </div>

      <p className="text-xs text-gray-500 mt-1">
        {fmt(m.total_input_tokens)} tokens embedded
      </p>

      <div className="mt-1.5">
        <div className="flex justify-between items-center">
          <p className="text-xs text-gray-500">Est. cost</p>
          <p className={`text-xs font-medium ${warn ? "text-red-500" : "text-gray-700"}`}>
            ${cost.toFixed(4)} / $10.00
          </p>
        </div>
        <ProgressBar pct={pct} color="bg-orange-400" />
        <p className={`text-[10px] mt-1 ${warn ? "text-red-500" : "text-gray-400"}`}>
          {warn ? "Low balance! " : ""}${remaining.toFixed(4)} remaining
        </p>
      </div>

      <p className="text-[10px] text-gray-400">Pricing: $0.12/1M tokens (approx.)</p>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

interface Props {
  models: ModelUsage[];
  title?: string;
}

export default function UsageStats({ models, title = "Model Usage" }: Props) {
  if (models.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
      <div className="flex flex-wrap gap-3">
        {models.map((m) =>
          m.model === "voyage-3" ? (
            <VoyageCard key={m.model} m={m} />
          ) : m.model.startsWith("gemini") ? (
            <GeminiCard key={m.model} m={m} />
          ) : (
            <ClaudeCard key={m.model} m={m} />
          )
        )}
      </div>
    </div>
  );
}
