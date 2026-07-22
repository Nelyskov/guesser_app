"use client";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { fetchJson, postJson } from "@/lib/api";

type Phase = "loading" | "guess" | "reveal" | "gameover";

interface Product { id: number; name: string; image_url: string; site: string; }
interface Pair { left: Product; right: Product; }

export default function HigherGame() {
  const [phase, setPhase]       = useState<Phase>("loading");
  const [pair, setPair]         = useState<Pair | null>(null);
  const [prices, setPrices]     = useState<{ left_price: number; right_price: number } | null>(null);
  const [choice, setChoice]     = useState<"left" | "right" | null>(null);
  const [correct, setCorrect]   = useState(false);
  const [streak, setStreak]     = useState(0);
  const [best, setBest]         = useState(0);
  const [score, setScore]       = useState(0);
  const [round, setRound]       = useState(0);
  const [nickname, setNickname] = useState("Аноним");
  const [saved, setSaved]       = useState(false);

  const loadPair = useCallback(async () => {
    setPhase("loading");
    setPrices(null);
    setChoice(null);
    try {
      const p = await fetchJson<Pair>("/product/pair");
      setPair(p);
      setPhase("guess");
    } catch {
      alert("Ошибка загрузки. Проверь базу данных.");
    }
  }, []);

  useEffect(() => { loadPair(); }, [loadPair]);

  async function handleChoice(side: "left" | "right") {
    if (!pair || phase !== "guess") return;
    setChoice(side);

    const data = await fetchJson<{ left_price: number; right_price: number }>(
      `/product/pair/reveal/${pair.left.id}/${pair.right.id}`
    );
    setPrices(data);

    const isCorrect =
      (side === "left"  && data.left_price  >= data.right_price) ||
      (side === "right" && data.right_price >= data.left_price);

    setCorrect(isCorrect);
    setRound(r => r + 1);

    if (isCorrect) {
      const newStreak = streak + 1;
      setStreak(newStreak);
      setBest(b => Math.max(b, newStreak));
      const pts = 100 + newStreak * 50; // бонус за серию
      setScore(s => s + pts);
    } else {
      setStreak(0);
    }
    setPhase("reveal");
  }

  async function handleSave() {
    await postJson("/score", { mode: "higher", nickname, score, rounds: round });
    setSaved(true);
  }

  // Через 10 неправильных ответов — конец
  const lives = 3;
  const [wrongs, setWrongs] = useState(0);

  async function handleNext() {
    if (!correct && wrongs + 1 >= lives) {
      setWrongs(w => w + 1);
      setPhase("gameover");
      return;
    }
    if (!correct) setWrongs(w => w + 1);
    await loadPair();
  }

  // ── gameover ─────────────────────────────────────────────────
  if (phase === "gameover") return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 text-center">
      <div className="font-display text-[#ff2d55] text-7xl mb-2">GAME OVER</div>
      <div className="font-display text-[#f5f0e8] text-4xl mb-2">{score.toLocaleString("ru")} очков</div>
      <div className="font-mono text-[#f5f0e8]/50 mb-8">
        Лучшая серия: {best} · Раундов: {round}
      </div>

      {!saved ? (
        <div className="flex flex-col items-center gap-4 mb-8">
          <input
            value={nickname} onChange={e => setNickname(e.target.value)}
            placeholder="Ваш никнейм"
            className="bg-[#1a1a2e] border border-[#f5f0e8]/20 rounded-xl px-4 py-3
                       text-[#f5f0e8] font-body text-center w-64 focus:outline-none
                       focus:border-[#ff2d55]"
          />
          <button onClick={handleSave}
            className="bg-[#ff2d55] text-white font-body font-bold px-8 py-3
                       rounded-xl hover:bg-[#ff5577] transition-colors">
            Сохранить
          </button>
        </div>
      ) : (
        <div className="text-[#ff2d55] font-mono mb-8">✓ Сохранено!</div>
      )}

      <div className="flex gap-4">
        <button onClick={() => {
          setRound(0); setScore(0); setStreak(0); setBest(0);
          setWrongs(0); setSaved(false); loadPair();
        }}
          className="border border-[#ff2d55] text-[#ff2d55] font-body px-6 py-3
                     rounded-xl hover:bg-[#ff2d55]/10 transition-colors">
          Снова
        </button>
        <Link href="/"
          className="border border-[#f5f0e8]/20 text-[#f5f0e8]/60 font-body px-6 py-3
                     rounded-xl hover:border-[#f5f0e8]/50 transition-colors">
          Главная
        </Link>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col">

      {/* Хедер */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[#f5f0e8]/5">
        <Link href="/" className="font-display text-xl text-[#ff2d55]">PG</Link>
        <div className="flex items-center gap-6">
          {/* Жизни */}
          <div className="flex gap-1">
            {Array.from({ length: lives }).map((_, i) => (
              <span key={i} className={`text-lg ${i < lives - wrongs ? "opacity-100" : "opacity-20"}`}>
                ❤️
              </span>
            ))}
          </div>
          {streak > 1 && (
            <div className="font-mono text-[#ff2d55] text-sm">🔥 ×{streak}</div>
          )}
          <div className="font-display text-2xl text-[#ff2d55]">
            {score.toLocaleString("ru")}
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-8 max-w-4xl mx-auto w-full">

        {phase === "loading" && (
          <div className="text-[#f5f0e8]/30 font-mono animate-pulse">Загрузка...</div>
        )}

        {(phase === "guess" || phase === "reveal") && pair && (
          <>
            <div className="text-center mb-8">
              <h1 className="font-display text-3xl text-[#f5f0e8]">ЧТО ДОРОЖЕ?</h1>
              {phase === "reveal" && (
                <div className={`font-display text-2xl mt-1 reveal
                  ${correct ? "text-[#c8ff00]" : "text-[#ff2d55]"}`}>
                  {correct ? "✓ ВЕРНО!" : "✗ НЕВЕРНО"}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 w-full">
              {(["left", "right"] as const).map(side => {
                const p = pair[side];
                const price = prices?.[`${side}_price`];
                const isChosen = choice === side;
                const isWinner = prices
                  ? (side === "left"
                    ? prices.left_price >= prices.right_price
                    : prices.right_price >= prices.left_price)
                  : false;

                let borderColor = "border-[#f5f0e8]/10 hover:border-[#ff2d55]";
                if (phase === "reveal") {
                  if (isWinner) borderColor = "border-[#c8ff00]";
                  else if (isChosen) borderColor = "border-[#ff2d55]";
                  else borderColor = "border-[#f5f0e8]/5";
                }

                return (
                  <button key={side}
                    onClick={() => handleChoice(side)}
                    disabled={phase === "reveal"}
                    className={`group relative bg-[#1a1a2e] rounded-2xl overflow-hidden
                               border-2 transition-all duration-300 text-left
                               ${borderColor}
                               ${phase === "guess" ? "cursor-pointer" : "cursor-default"}
                               ${phase === "reveal" && !isWinner && !isChosen ? "opacity-50" : ""}`}
                  >
                    {/* Изображение */}
                    <div className="aspect-square bg-[#0a0a0f] flex items-center justify-center relative">
                      <img
                        src={p.image_url} alt={p.name}
                        className="w-full h-full object-contain p-3"
                        onError={e => { (e.target as HTMLImageElement).src = "/placeholder.png"; }}
                      />
                      {phase === "guess" && (
                        <div className="absolute inset-0 bg-[#ff2d55]/0
                                       group-hover:bg-[#ff2d55]/5 transition-colors" />
                      )}
                      {phase === "reveal" && isWinner && (
                        <div className="absolute top-2 right-2 bg-[#c8ff00] text-[#0a0a0f]
                                       font-display text-lg px-2 py-0.5 rounded-lg reveal">
                          WIN
                        </div>
                      )}
                    </div>

                    {/* Инфо */}
                    <div className="p-3">
                      <p className="font-body text-[#f5f0e8] text-xs line-clamp-2 mb-2">
                        {p.name}
                      </p>
                      <div className="font-mono text-[#f5f0e8]/30 text-xs">{p.site}</div>

                      {phase === "reveal" && price !== undefined && (
                        <div className={`font-display text-2xl mt-2 reveal
                          ${isWinner ? "text-[#c8ff00]" : "text-[#f5f0e8]/60"}`}>
                          {price.toLocaleString("ru")} ₽
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {phase === "reveal" && (
              <button onClick={handleNext}
                className="mt-6 w-full max-w-sm bg-[#1a1a2e] border border-[#f5f0e8]/20
                           text-[#f5f0e8] font-body font-medium text-lg py-4 rounded-2xl
                           hover:border-[#ff2d55] hover:text-[#ff2d55] transition-all reveal">
                Следующая пара →
              </button>
            )}
          </>
        )}
      </main>
    </div>
  );
}
