'use client';

import { useEffect, useState } from "react";

export default function SaveOnLoad({ deckId }: { deckId: string }) {
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (saved) return;

    fetch(`/api/save-deck?deckId=${encodeURIComponent(deckId)}`, {
      method: "POST",
    }).finally(() => setSaved(true));
  }, [deckId, saved]);

  return null;
}
