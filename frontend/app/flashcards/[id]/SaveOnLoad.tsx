"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type SaveOnLoadProps = {
  deckId: string;
  title?: string | null;
  sourceType?: string | null;
  sourceLabel?: string | null;
};

export default function SaveOnLoad({
  deckId,
  title,
  sourceType,
  sourceLabel,
}: SaveOnLoadProps) {
  const router = useRouter();
  
  // CRITICAL FIX: Don't render at all if no title - prevents overwriting existing good titles
  if (!deckId || !title) {
    console.warn("[SaveOnLoad] Skipping save because deckId or title is missing", { deckId, title });
    return null;
  }

  const [done, setDone] = useState(false);

  useEffect(() => {
    let aborted = false;
    if (done) return;

    (async () => {
      try {
        const payload = {
          deckId,
          title,
          sourceType: sourceType ?? null,
          sourceLabel: sourceLabel ?? title ?? null,
        };
        console.log("[SaveOnLoad] POSTing to /api/save-deck:", payload);
        const res = await fetch("/api/save-deck", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        });
        const json = await res.json().catch(() => ({}));
        if (!aborted) {
          if (!json?.ok) {
            console.warn("[SaveOnLoad] save-deck failed", { deckId, json });
          } else {
            console.log("[SaveOnLoad] save-deck succeeded, refreshing router");
            // Refresh router to update /saved page cache
            router.refresh();
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
  }, [deckId, title, sourceType, sourceLabel, done]);

  return null;
}
