"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchJson } from "@/lib/api";

interface Entry { nickname: string; score: number; rounds: number; date: string; }

export default function Leaderboard() {
  const [mode, setMode]       = useState<"slider" | "higher">("slider");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchJson<{ leaderboard: Entry[] }>(`/leaderboard/${mode}`)
      .then(d => setEntries(d.leaderboard))
      .finally(() => setLoading(false));
  }, [mode]);

  const medals = ["🥇", "🥈", "🥉"];

  return (
    <div className="min-h-screen flex flex-col max-w-2xl mx-auto px-4 py-8">
      <header className="flex items-center justify-between mb-10">
        <Link href="/" className="font-display text-xl text-[#c8ff00]">← PG</Link>
        <h1 className="font-display text-3xl text-[#f5f0e8]">ЛИДЕРЫ</h1>
      </header>

      {/* Переключатель */}
      <div className="flex bg-[#1a1a2e] rounded-xl p-1 mb-8">
        {(["slider", "higher"] as const).map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={`flex-1 py-2 rounded-lg font-body font-medium text-sm transition-all
              ${mode === m
                ? "bg-[#c8ff00] text-[#0a0a0f]"
                : "text-[#f5f0e8]/40 hover:text-[#f5f0e8]/70"}`}>
            {m === "slider" ? "🎯 Угадай цену" : "⚔️ Что дороже"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-[#f5f0e8]/30 font-mono text-center animate-pulse">Загрузка...</div>
      ) : entries.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-5xl mb-4">🏆</div>
          <div className="text-[#f5f0e8]/40 font-body">Пока никто не играл</div>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((e, i) => (
            <div key={i}
              className={`flex items-center gap-4 p-4 rounded-xl border transition-all
                ${i === 0
                  ? "bg-[#c8ff00]/10 border-[#c8ff00]/30"
                  : "bg-[#1a1a2e] border-[#f5f0e8]/5"}`}>
              <div className="text-2xl w-8 text-center">
                {medals[i] ?? <span className="font-mono text-[#f5f0e8]/30 text-sm">{i + 1}</span>}
              </div>
              <div className="flex-1">
                <div className={`font-body font-medium ${i === 0 ? "text-[#c8ff00]" : "text-[#f5f0e8]"}`}>
                  {e.nickname}
                </div>
                <div className="font-mono text-xs text-[#f5f0e8]/30">
                  {e.rounds} раундов · {e.date}
                </div>
              </div>
              <div className={`font-display text-2xl ${i === 0 ? "text-[#c8ff00]" : "text-[#f5f0e8]"}`}>
                {e.score.toLocaleString("ru")}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
