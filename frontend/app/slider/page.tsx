"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { fetchJson, postJson } from "@/lib/api";

type Phase = "loading" | "guess" | "reveal" | "gameover";

interface Product {
  id: number;
  name: string;
  image_url: string;
  site: string;
}

const ROUNDS = 5;
const MAX_PRICE = 200000;

function calcScore(guess: number, real: number): number {
  const diff = Math.abs(guess - real) / real;
  if (diff <= 0.02) return 1000;
  if (diff <= 0.05) return 800;
  if (diff <= 0.10) return 600;
  if (diff <= 0.20) return 400;
  if (diff <= 0.40) return 200;
  return 50;
}

export default function SliderGame() {
  const [phase, setPhase]         = useState<Phase>("loading");
  const [product, setProduct]     = useState<Product | null>(null);
  const [realPrice, setRealPrice] = useState(0);
  const [guess, setGuess]         = useState(10000);
  const [round, setRound]         = useState(1);
  const [totalScore, setTotalScore] = useState(0);
  const [roundScore, setRoundScore] = useState(0);
  const [nickname, setNickname]   = useState("Аноним");
  const [saved, setSaved]         = useState(false);
  const [shaking, setShaking]     = useState(false);
  const sliderRef = useRef<HTMLInputElement>(null);

  const loadProduct = useCallback(async () => {
    setPhase("loading");
    try {
      const p = await fetchJson<Product>("/product/random");
      setProduct(p);
      setGuess(10000);
      setPhase("guess");
    } catch {
      alert("Ошибка загрузки товара. Проверь что парсер наполнил базу.");
    }
  }, []);

  useEffect(() => { loadProduct(); }, [loadProduct]);

  // Обновляем CSS переменную ползунка
  useEffect(() => {
    if (sliderRef.current) {
      const pct = ((guess - 100) / (MAX_PRICE - 100)) * 100;
      sliderRef.current.style.setProperty("--pct", `${pct}%`);
    }
  }, [guess]);

  async function handleGuess() {
    if (!product) return;
    try {
      const { price } = await fetchJson<{ price: number }>(`/product/${product.id}/price`);
      setRealPrice(price);
      const sc = calcScore(guess, price);
      setRoundScore(sc);
      setTotalScore(s => s + sc);

      if (sc < 400) {
        setShaking(true);
        setTimeout(() => setShaking(false), 500);
      }
      setPhase("reveal");
    } catch {
      alert("Ошибка получения цены");
    }
  }

  async function handleNext() {
    if (round >= ROUNDS) {
      setPhase("gameover");
    } else {
      setRound(r => r + 1);
      await loadProduct();
    }
  }

  async function handleSave() {
    await postJson("/score", { mode: "slider", nickname, score: totalScore, rounds: ROUNDS });
    setSaved(true);
  }

  const pctOff = realPrice ? Math.round(Math.abs(guess - realPrice) / realPrice * 100) : 0;

  // ── UI ──────────────────────────────────────────────────────────
  if (phase === "gameover") return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 text-center">
      <div className="font-display text-[#c8ff00] text-8xl mb-2">ФИНИШ</div>
      <div className="font-display text-[#f5f0e8] text-5xl mb-8">{totalScore.toLocaleString("ru")} очков</div>

      {!saved ? (
        <div className="flex flex-col items-center gap-4 mb-8">
          <input
            value={nickname} onChange={e => setNickname(e.target.value)}
            placeholder="Ваш никнейм"
            className="bg-[#1a1a2e] border border-[#f5f0e8]/20 rounded-xl px-4 py-3
                       text-[#f5f0e8] font-body text-center w-64 focus:outline-none
                       focus:border-[#c8ff00]"
          />
          <button onClick={handleSave}
            className="bg-[#c8ff00] text-[#0a0a0f] font-body font-bold px-8 py-3
                       rounded-xl hover:bg-white transition-colors">
            Сохранить результат
          </button>
        </div>
      ) : (
        <div className="text-[#c8ff00] font-mono mb-8">✓ Результат сохранён!</div>
      )}

      <div className="flex gap-4">
        <button onClick={() => { setRound(1); setTotalScore(0); setSaved(false); loadProduct(); setPhase("guess"); }}
          className="border border-[#c8ff00] text-[#c8ff00] font-body px-6 py-3 rounded-xl
                     hover:bg-[#c8ff00]/10 transition-colors">
          Играть снова
        </button>
        <Link href="/"
          className="border border-[#f5f0e8]/20 text-[#f5f0e8]/60 font-body px-6 py-3
                     rounded-xl hover:border-[#f5f0e8]/50 transition-colors">
          На главную
        </Link>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col">

      {/* Хедер */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[#f5f0e8]/5">
        <Link href="/" className="font-display text-xl text-[#c8ff00]">PG</Link>
        <div className="flex items-center gap-6">
          <span className="font-mono text-[#f5f0e8]/40 text-sm">
            Раунд {round}/{ROUNDS}
          </span>
          <span className="font-display text-2xl text-[#c8ff00]">
            {totalScore.toLocaleString("ru")}
          </span>
        </div>
      </header>

      {/* Прогресс */}
      <div className="h-1 bg-[#f5f0e8]/5">
        <div className="h-full bg-[#c8ff00] transition-all duration-500"
          style={{ width: `${((round - 1) / ROUNDS) * 100}%` }} />
      </div>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-8 max-w-2xl mx-auto w-full">

        {phase === "loading" && (
          <div className="text-[#f5f0e8]/30 font-mono animate-pulse">Загрузка...</div>
        )}

        {(phase === "guess" || phase === "reveal") && product && (
          <div className={`w-full reveal ${shaking ? "shake" : ""}`}>

            {/* Карточка товара */}
            <div className="bg-[#1a1a2e] rounded-2xl overflow-hidden mb-8 border border-[#f5f0e8]/5">
              <div className="relative aspect-square max-h-72 bg-[#0a0a0f] flex items-center justify-center">
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="w-full h-full object-contain p-4"
                  onError={e => { (e.target as HTMLImageElement).src = "/placeholder.png"; }}
                />
                <div className="absolute top-3 right-3 bg-[#0a0a0f]/80 backdrop-blur
                               px-2 py-1 rounded-lg text-xs font-mono text-[#f5f0e8]/50">
                  {product.site}
                </div>
              </div>
              <div className="p-4">
                <h2 className="font-body font-medium text-[#f5f0e8] text-base leading-snug line-clamp-2">
                  {product.name}
                </h2>
              </div>
            </div>

            {/* Ползунок */}
            <div className="mb-8">
              <div className="flex justify-between items-center mb-4">
                <span className="font-mono text-[#f5f0e8]/40 text-sm">100 ₽</span>
                <div className="text-center">
                  <div className="font-display text-5xl text-[#c8ff00]">
                    {guess.toLocaleString("ru")} ₽
                  </div>
                  {phase === "reveal" && (
                    <div className="font-mono text-sm mt-1">
                      {pctOff <= 5
                        ? <span className="text-[#c8ff00]">🎯 Погрешность {pctOff}%</span>
                        : <span className="text-[#ff2d55]">Погрешность {pctOff}%</span>
                      }
                    </div>
                  )}
                </div>
                <span className="font-mono text-[#f5f0e8]/40 text-sm">200к ₽</span>
              </div>

              <input
                ref={sliderRef}
                type="range"
                min={100} max={MAX_PRICE}
                value={guess}
                onChange={e => setGuess(Number(e.target.value))}
                disabled={phase === "reveal"}
                className="price-slider w-full"
              />
            </div>

            {/* Ответ */}
            {phase === "reveal" && (
              <div className="bg-[#1a1a2e] rounded-2xl p-6 mb-6 text-center reveal">
                <div className="font-body text-[#f5f0e8]/50 text-sm mb-1">Настоящая цена</div>
                <div className="font-display text-5xl text-[#f5f0e8] mb-3">
                  {realPrice.toLocaleString("ru")} ₽
                </div>
                <div className={`font-display text-3xl ${roundScore >= 600 ? "text-[#c8ff00]" : "text-[#ff2d55]"}`}>
                  +{roundScore} очков
                </div>
              </div>
            )}

            {/* Кнопка */}
            {phase === "guess" ? (
              <button onClick={handleGuess}
                className="w-full bg-[#c8ff00] text-[#0a0a0f] font-body font-bold
                           text-lg py-4 rounded-2xl hover:bg-white transition-colors
                           pulse-acid">
                Это моя цена! 💰
              </button>
            ) : (
              <button onClick={handleNext}
                className="w-full bg-[#1a1a2e] border border-[#f5f0e8]/20 text-[#f5f0e8]
                           font-body font-medium text-lg py-4 rounded-2xl
                           hover:border-[#c8ff00] hover:text-[#c8ff00] transition-all">
                {round >= ROUNDS ? "Посмотреть результат →" : "Следующий товар →"}
              </button>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
