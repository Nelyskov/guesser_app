"use client";
import Link from "next/link";
import { useState, useEffect } from "react";
import { fetchJson } from "@/lib/api";

export default function Home() {
  const [stats, setStats] = useState<{ total: number; sites: number; avg_price: number } | null>(null);

  useEffect(() => {
    fetchJson<typeof stats>("/stats").then(setStats).catch(() => {});
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 relative">

      {/* Декоративная сетка */}
      <div className="fixed inset-0 opacity-5 pointer-events-none"
        style={{
          backgroundImage: "linear-gradient(rgba(200,255,0,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(200,255,0,0.5) 1px, transparent 1px)",
          backgroundSize: "60px 60px"
        }} />

      {/* Заголовок */}
      <div className="text-center mb-16 relative z-10">
        <div className="inline-block bg-[#c8ff00] text-[#0a0a0f] px-4 py-1 text-sm font-mono font-bold mb-6 tracking-widest uppercase">
          Beta
        </div>
        <h1 className="font-display text-[clamp(4rem,15vw,12rem)] leading-none tracking-tight text-[#f5f0e8]">
          PRICE
          <br />
          <span className="text-[#c8ff00]">GUESSER</span>
        </h1>
        <p className="text-[#f5f0e8]/50 font-body mt-4 text-lg max-w-md mx-auto">
          Угадай цену товара — кто точнее, тот и победил
        </p>

        {stats && (
          <div className="flex gap-8 justify-center mt-6">
            {[
              { label: "товаров", value: stats.total.toLocaleString("ru") },
              { label: "сайтов", value: stats.sites },
              { label: "ср. цена", value: stats.avg_price.toLocaleString("ru") + " ₽" },
            ].map(s => (
              <div key={s.label} className="text-center">
                <div className="font-display text-2xl text-[#c8ff00]">{s.value}</div>
                <div className="text-xs text-[#f5f0e8]/40 uppercase tracking-widest">{s.label}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Режимы */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl relative z-10">

        <Link href="/slider" className="group">
          <div className="border border-[#f5f0e8]/10 hover:border-[#c8ff00] bg-[#1a1a2e]/60
                         backdrop-blur rounded-2xl p-8 transition-all duration-300
                         hover:bg-[#c8ff00]/5 cursor-pointer">
            <div className="text-5xl mb-4">🎯</div>
            <h2 className="font-display text-4xl text-[#f5f0e8] mb-2 group-hover:text-[#c8ff00] transition-colors">
              УГАДАЙ ЦЕНУ
            </h2>
            <p className="text-[#f5f0e8]/50 text-sm leading-relaxed">
              Видишь товар — двигай ползунок, угадывай цену.
              Чем точнее — тем больше очков.
            </p>
            <div className="mt-6 flex items-center gap-2 text-[#c8ff00] text-sm font-mono">
              <span>Играть</span>
              <span className="group-hover:translate-x-2 transition-transform inline-block">→</span>
            </div>
          </div>
        </Link>

        <Link href="/higher" className="group">
          <div className="border border-[#f5f0e8]/10 hover:border-[#ff2d55] bg-[#1a1a2e]/60
                         backdrop-blur rounded-2xl p-8 transition-all duration-300
                         hover:bg-[#ff2d55]/5 cursor-pointer">
            <div className="text-5xl mb-4">⚔️</div>
            <h2 className="font-display text-4xl text-[#f5f0e8] mb-2 group-hover:text-[#ff2d55] transition-colors">
              ЧТО ДОРОЖЕ
            </h2>
            <p className="text-[#f5f0e8]/50 text-sm leading-relaxed">
              Два товара — выбери тот, что дороже.
              Серия побед строит стрик.
            </p>
            <div className="mt-6 flex items-center gap-2 text-[#ff2d55] text-sm font-mono">
              <span>Играть</span>
              <span className="group-hover:translate-x-2 transition-transform inline-block">→</span>
            </div>
          </div>
        </Link>
      </div>

      {/* Лидерборды */}
      <div className="mt-10 relative z-10">
        <Link href="/leaderboard"
          className="text-[#f5f0e8]/30 hover:text-[#f5f0e8]/70 text-sm font-mono
                     transition-colors underline underline-offset-4">
          Таблица лидеров
        </Link>
      </div>
    </main>
  );
}
