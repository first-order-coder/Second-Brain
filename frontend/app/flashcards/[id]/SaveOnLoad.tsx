"use client";

import { useEffect, useState } from "react";

export default function SaveOnLoad({ deckId }: { deckId: string }) {
  const [done, setDone] = useState(false);

  useEffect(() => {
    let aborted = false;
    if (!deckId || done) return;

    (async () => {
      try {
        const res = await fetch("/api/save-deck", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ deckId }),
        });
        const json = await res.json().catch(() => ({}));
        if (!aborted) {
          if (!json?.ok) {
            console.warn("[SaveOnLoad] save-deck failed", { deckId, json });
          }
          setDone(true);
        }
      } catch (error) {
        if (!aborted) {
          console.warn("[SaveOnLoad] save-deck error", { deckId, error });
          setDone(true);
        }
      }
    })();

    return () => {
      aborted = true;
    };
  }, [deckId, done]);

  return null;
}
