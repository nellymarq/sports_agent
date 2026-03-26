"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ParlayLeg {
  fighter: string;
  odds: string;
}

interface BetSizeResult {
  recommended_size: number;
  edge_pct: number;
  kelly_fraction: number;
  risk_level: string;
  expected_value: number;
}

interface OddsConversion {
  american: string;
  decimal: number | null;
  implied_probability: number;
  implied_pct: string;
}

export default function BetCalculatorPage() {
  const [activeTab, setActiveTab] = useState<"parlay" | "kelly" | "convert">("parlay");

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">Bet Calculator</h1>
      <p className="text-sm text-slate-400 mb-6">
        Parlay builder, Kelly criterion sizing, and odds converter
      </p>

      <div className="flex gap-2 mb-6">
        {(["parlay", "kelly", "convert"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-accent text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab === "parlay" ? "Parlay Builder" : tab === "kelly" ? "Kelly Sizing" : "Odds Converter"}
          </button>
        ))}
      </div>

      {activeTab === "parlay" && <ParlayBuilder />}
      {activeTab === "kelly" && <KellySizing />}
      {activeTab === "convert" && <OddsConverter />}
    </div>
  );
}

function ParlayBuilder() {
  const [legs, setLegs] = useState<ParlayLeg[]>([
    { fighter: "", odds: "" },
    { fighter: "", odds: "" },
  ]);
  const [stake, setStake] = useState("100");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const updateLeg = (idx: number, field: keyof ParlayLeg, val: string) => {
    setLegs((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: val } : l)));
  };

  const addLeg = () => setLegs((prev) => [...prev, { fighter: "", odds: "" }]);
  const removeLeg = (idx: number) => setLegs((prev) => prev.filter((_, i) => i !== idx));

  const calculate = async () => {
    const validLegs = legs.filter((l) => l.odds.trim());
    if (validLegs.length < 2) return;

    setLoading(true);
    try {
      const res = await fetch(`${API}/parlay/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          legs: validLegs.map((l) => ({
            fighter: l.fighter || "Fighter",
            american_odds: l.odds,
          })),
          stake: parseFloat(stake) || 100,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setResult({ error: "Failed to calculate parlay" });
    }
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {legs.map((leg, idx) => (
          <div key={idx} className="flex gap-2 items-center">
            <span className="text-xs text-slate-500 w-8">#{idx + 1}</span>
            <input
              type="text"
              placeholder="Fighter name"
              value={leg.fighter}
              onChange={(e) => updateLeg(idx, "fighter", e.target.value)}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Odds (e.g. -150)"
              value={leg.odds}
              onChange={(e) => updateLeg(idx, "odds", e.target.value)}
              className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            {legs.length > 2 && (
              <button
                onClick={() => removeLeg(idx)}
                className="text-red-400 hover:text-red-300 text-sm px-2"
              >
                X
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-3 items-center">
        <button
          onClick={addLeg}
          className="text-sm text-accent hover:text-accent/80 transition-colors"
        >
          + Add Leg
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <label className="text-xs text-slate-400">Stake $</label>
          <input
            type="number"
            value={stake}
            onChange={(e) => setStake(e.target.value)}
            className="w-24 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      <button
        onClick={calculate}
        disabled={loading}
        className="w-full bg-accent hover:bg-accent/90 text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
      >
        {loading ? "Calculating..." : "Calculate Parlay"}
      </button>

      {result && !result.error && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-slate-400">Combined Odds</div>
              <div className="text-lg font-bold">
                {result.combined_american_odds || "N/A"}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Implied Probability</div>
              <div className="text-lg font-bold">
                {result.implied_probability
                  ? `${(result.implied_probability * 100).toFixed(1)}%`
                  : "N/A"}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Potential Payout</div>
              <div className="text-lg font-bold text-green-400">
                ${result.potential_payout?.toFixed(2) || "N/A"}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Profit</div>
              <div className="text-lg font-bold text-green-400">
                ${result.profit?.toFixed(2) || "N/A"}
              </div>
            </div>
          </div>
          {result.legs && (
            <div className="pt-3 border-t border-slate-700">
              <div className="text-xs text-slate-400 mb-2">Leg Breakdown</div>
              {result.legs.map((leg: any, i: number) => (
                <div key={i} className="flex justify-between text-sm py-1">
                  <span>{leg.fighter}</span>
                  <span className="text-slate-400">
                    {leg.american_odds} ({(leg.implied_probability * 100).toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {result?.error && (
        <div className="text-red-400 text-sm">{result.error}</div>
      )}
    </div>
  );
}

function KellySizing() {
  const [bankroll, setBankroll] = useState("1000");
  const [odds, setOdds] = useState("");
  const [modelProb, setModelProb] = useState("");
  const [result, setResult] = useState<BetSizeResult | null>(null);
  const [loading, setLoading] = useState(false);

  const calculate = async () => {
    if (!odds || !modelProb) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/bet/size`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bankroll: parseFloat(bankroll) || 1000,
          american_odds: odds,
          model_probability: parseFloat(modelProb) / 100,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setResult(null);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="text-xs text-slate-400 block mb-1">Bankroll ($)</label>
          <input
            type="number"
            value={bankroll}
            onChange={(e) => setBankroll(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400 block mb-1">American Odds</label>
          <input
            type="text"
            placeholder="-150"
            value={odds}
            onChange={(e) => setOdds(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400 block mb-1">Model Win % </label>
          <input
            type="number"
            placeholder="65"
            value={modelProb}
            onChange={(e) => setModelProb(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      <button
        onClick={calculate}
        disabled={loading}
        className="w-full bg-accent hover:bg-accent/90 text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
      >
        {loading ? "Calculating..." : "Calculate Bet Size"}
      </button>

      {result && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-slate-400">Recommended Bet</div>
              <div className="text-lg font-bold text-green-400">
                ${result.recommended_size?.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Edge</div>
              <div className="text-lg font-bold">
                {result.edge_pct !== undefined ? `${(result.edge_pct * 100).toFixed(1)}%` : "N/A"}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Kelly Fraction</div>
              <div className="text-lg font-bold">
                {result.kelly_fraction !== undefined
                  ? `${(result.kelly_fraction * 100).toFixed(1)}%`
                  : "N/A"}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Risk Level</div>
              <div
                className={`text-lg font-bold ${
                  result.risk_level === "low"
                    ? "text-green-400"
                    : result.risk_level === "medium"
                    ? "text-yellow-400"
                    : "text-red-400"
                }`}
              >
                {result.risk_level?.toUpperCase() || "N/A"}
              </div>
            </div>
          </div>
          {result.expected_value !== undefined && (
            <div className="pt-3 border-t border-slate-700">
              <div className="text-xs text-slate-400">Expected Value per Bet</div>
              <div
                className={`text-sm font-medium ${
                  result.expected_value > 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                ${result.expected_value?.toFixed(2)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function OddsConverter() {
  const [input, setInput] = useState("");
  const [format, setFormat] = useState<"american" | "decimal">("american");
  const [result, setResult] = useState<OddsConversion | null>(null);

  const convert = async () => {
    if (!input) return;
    try {
      const param = format === "american" ? `american=${input}` : `decimal=${input}`;
      const res = await fetch(`${API}/odds/convert?${param}`);
      const data = await res.json();
      setResult(data);
    } catch {
      setResult(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="text-xs text-slate-400 block mb-1">
            {format === "american" ? "American Odds (e.g. -150 or +200)" : "Decimal Odds (e.g. 1.67)"}
          </label>
          <input
            type="text"
            placeholder={format === "american" ? "-150" : "1.67"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && convert()}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <button
          onClick={() => setFormat(format === "american" ? "decimal" : "american")}
          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-400 hover:text-slate-200"
        >
          Switch to {format === "american" ? "Decimal" : "American"}
        </button>
        <button
          onClick={convert}
          className="px-4 py-2 bg-accent hover:bg-accent/90 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Convert
        </button>
      </div>

      {result && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-xs text-slate-400">American</div>
              <div className="text-lg font-bold">{result.american}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Decimal</div>
              <div className="text-lg font-bold">{result.decimal?.toFixed(3) || "N/A"}</div>
            </div>
            <div>
              <div className="text-xs text-slate-400">Implied Probability</div>
              <div className="text-lg font-bold">{result.implied_pct}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
