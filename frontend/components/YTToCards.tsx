"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card as UICard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
// Slider removed - fixed 10 cards for YouTube
import { Separator } from "@/components/ui/separator";
import { YouTubeFlashcardsResponse } from "@/lib/types";

type CardItem = {
  front: string; 
  back: string; 
  cloze?: string | null;
  start_s?: number | null; 
  end_s?: number | null;
  evidence?: string | null; 
  difficulty?: "easy"|"medium"|"hard"|null;
  tags?: string[];
};

export default function YTToCards() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  // Fixed 10 cards for YouTube - no count selector needed
  const [allowAuto, setAllowAuto] = useState(true);
  const [useCookies, setUseCookies] = useState(false);
  const [enableFallback, setEnableFallback] = useState(false);
  const [langHint, setLangHint] = useState<string[]>(["en","en-US","en-GB"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resp, setResp] = useState<YouTubeFlashcardsResponse | null>(null);
  const [lastDeckId, setLastDeckId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [tracks, setTracks] = useState<{
    video_id: string;
    tracks: Array<{lang: string; kind: string}>;
    gated: boolean;
  } | null>(null);
  const [checkingTracks, setCheckingTracks] = useState(false);

  const saveDeckSilently = useCallback((deckId: string) => {
    fetch("/api/save-deck", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ deckId }),
    })
      .then((res) => res.json().catch(() => ({})))
      .then((json) => {
        if (!json?.ok) {
          console.warn("[YTToCards] save-deck failed", { deckId, json });
        }
      })
      .catch((error) => {
        console.warn("[YTToCards] save-deck error", { deckId, error });
      });
  }, []);

  // Normalize paste (trim spaces/newlines)
  const onPasteLink = useCallback((e: React.ClipboardEvent<HTMLInputElement>) => {
    const text = e.clipboardData.getData("text");
    if (text) setUrl(text.trim());
  }, []);

  const canGenerate = useMemo(() => {
    return !!url && url.startsWith("http");
  }, [url]);

  async function onCheckTracks() {
    if (!url || !url.startsWith("http")) return;
    setCheckingTracks(true);
    setError(null);
    try {
      const r = await fetch(`/api/youtube/tracks?url=${encodeURIComponent(url)}`);
      const data = await r.json();
      if (!r.ok) {
        setError(data?.detail || "Failed to check tracks.");
      } else {
        setTracks(data);
        // Auto-adjust language hints if no English tracks
        const hasEnglish = data.tracks.some((t: any) => t.lang.startsWith('en'));
        if (!hasEnglish && data.tracks.length > 0) {
          const topLang = data.tracks[0].lang;
          setLangHint([topLang, "en"]);
        }
      }
    } catch (err: any) {
      setError("Network error checking tracks.");
    } finally {
      setCheckingTracks(false);
    }
  }

  async function onGenerate() {
    setLoading(true); 
    setError(null); 
    setResp(null);
    try {
      // Build payload - fixed 10 cards on server side
      const payload: any = {
        url,
        n_cards: 10, // Fixed value, server will enforce 10
        langHint,
        allow_auto_generated: allowAuto,
        use_cookies: useCookies,
        enable_fallback: enableFallback
      };
      
      // No requested_count sent - server will force 10
      
      const r = await fetch("/api/youtube/flashcards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await r.json();
      if (!r.ok) {
        if (data?.detail && typeof data.detail === 'object' && data.detail.next_steps) {
          setError(`${data.detail.detail}. Next steps: ${data.detail.next_steps.join(', ')}`);
        } else {
          setError(data?.detail || "Failed to generate flashcards.");
        }
      } else {
        setResp(data);
        // Auto-navigate to deck if deck_id is present (deck parity with PDF flow)
        if (data?.deck_id) {
          setLastDeckId(data.deck_id);
          saveDeckSilently(data.deck_id);
          router.push(`/flashcards/${data.deck_id}`);
        }
      }
    } catch (err: any) {
      setError("Network error or API unavailable.");
    } finally {
      setLoading(false);
    }
  }

  // mm:ss for timestamp link labels
  const fmt = (s?: number | null) => {
    const n = Math.max(0, Math.floor(s || 0));
    const m = Math.floor(n / 60);
    const ss = String(n % 60).padStart(2, "0");
    return `${m}:${ss}`;
  };

  async function onSaveAll() {
    if (!resp?.cards?.length) return;
    setSaving(true);
    setError(null);
    try {
      const r = await fetch("/api/youtube/flashcards", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: resp.url,
          video_id: resp.video_id,
          title: resp.title,
          lang: resp.lang,
          cards: resp.cards.map(c => ({ front: c.front, back: c.back, cloze: c.cloze, start_s: c.start_s, end_s: c.end_s, evidence: c.evidence, difficulty: c.difficulty, tags: c.tags }))
        })
      });
      const data = await r.json();
      if (!r.ok) {
        setError(data?.detail || "Failed to save deck.");
      } else {
        // Navigate to viewer for this synthetic deck id
        if (data?.pdf_id) {
          saveDeckSilently(data.pdf_id);
          window.location.href = `/flashcards/${data.pdf_id}`;
        } else {
          window.location.href = "/";
        }
      }
    } catch {
      setError("Network error while saving deck.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <UICard className="p-4 space-y-4">
      <div className="space-y-2">
        <Label htmlFor="yt-url">Paste YouTube URL</Label>
        <Input
          id="yt-url"
          placeholder="https://youtu.be/VIDEO_ID or https://www.youtube.com/watch?v=VIDEO_ID"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onPaste={onPasteLink}
        />
        <p className="text-xs text-muted-foreground">
          Paste a link, then click "Generate Flashcards". This will create <strong>10</strong> flashcards.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Info card about flashcard count */}
        <UICard className="p-3 space-y-3">
          <div className="text-sm font-medium mb-1">Flashcard count</div>
          <div className="text-sm text-muted-foreground">
            Always generates <span className="font-semibold">10</span> cards for YouTube.
          </div>
          <div className="text-xs text-muted-foreground mt-2">
            Count control removed for MVP reliability.
          </div>
        </UICard>

        {/* Options card */}
        <UICard className="p-3 space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="auto">Allow auto-generated captions</Label>
            <Switch id="auto" checked={allowAuto} onCheckedChange={setAllowAuto}/>
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="cookies">Use cookies (consent/age gate)</Label>
            <Switch id="cookies" checked={useCookies} onCheckedChange={setUseCookies}/>
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="fallback">Enable yt-dlp fallback</Label>
            <Switch id="fallback" checked={enableFallback} onCheckedChange={setEnableFallback}/>
          </div>
          {/* Optional: simple language selector */}
          <div className="pt-2">
            <Label className="text-sm">Languages (priority order)</Label>
            <Input
              className="mt-1"
              value={langHint.join(",")}
              onChange={(e)=>setLangHint(e.target.value.split(",").map(s=>s.trim()).filter(Boolean))}
              placeholder="en,en-US,en-GB"
            />
            <p className="text-xs text-muted-foreground">Comma-separated codes; en-* maps to en internally.</p>
          </div>
        </UICard>
      </div>

      <div className="space-y-2">
        <div className="flex gap-2">
          <Button onClick={onGenerate} disabled={!canGenerate || loading}>
            {loading ? "Generating…" : "Generate Flashcards"}
          </Button>
          <Button 
            variant="outline" 
            onClick={onCheckTracks} 
            disabled={!canGenerate || checkingTracks}
          >
            {checkingTracks ? "Checking…" : "Check Captions"}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          YouTube generation creates <span className="font-medium">10</span> flashcards by default.
          (Count control removed for MVP reliability.)
        </p>
        {error && <div className="text-sm text-red-600 p-2 bg-red-50 rounded">{error}</div>}
        
        {/* Persistent View Flashcards button for deck parity */}
        {lastDeckId && (
          <div className="pt-2">
            <Button 
              variant="default" 
              onClick={() => router.push(`/flashcards/${lastDeckId}`)}
              className="w-full"
            >
              View Flashcards
            </Button>
          </div>
        )}
      </div>

      {tracks && (
        <UICard className="p-3 text-sm space-y-2">
          <div className="font-medium">Available Captions:</div>
          {tracks.gated && (
            <div className="text-amber-600 bg-amber-50 p-2 rounded">
              ⚠️ This video appears to be age/consent restricted. Enable cookies for better access.
            </div>
          )}
          {tracks.tracks.length > 0 ? (
            <div className="space-y-1">
              {tracks.tracks.map((track, i) => (
                <div key={i} className="flex justify-between text-xs">
                  <span className="font-mono">{track.lang}</span>
                  <span className={`px-2 py-1 rounded text-xs ${
                    track.kind === 'manual' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {track.kind}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500">No captions available</div>
          )}
        </UICard>
      )}

      {resp?.warnings?.length ? (
        <UICard className="p-3 text-sm">
          <strong>Warnings:</strong> {resp.warnings.join(" • ")}
        </UICard>
      ) : null}

      {resp?.cards?.length ? (
        <>
          <Separator />
          <div className="space-y-3">
            {resp.cards.map((c, i) => (
              <UICard key={i} className="p-3 space-y-2">
                <div className="text-xs text-muted-foreground">
                  Source: YouTube •{" "}
                  <a className="underline" target="_blank" href={`${resp.url}?t=${Math.floor(c.start_s || 0)}`}>
                    Open at {fmt(c.start_s)}
                  </a>
                </div>
                {/* If you have an Inline Card Editor, mount it here. Otherwise show plain fields. */}
                <div className="font-medium">Q: {c.front}</div>
                <div className="text-sm">A: {c.back}</div>
                {c.cloze ? <div className="text-sm italic">Cloze: {c.cloze}</div> : null}
                {c.evidence ? <div className="text-xs text-muted-foreground">"{c.evidence}"</div> : null}
              </UICard>
            ))}
          </div>
          <div className="pt-2">
            <Button variant="secondary" onClick={onSaveAll} disabled={saving}>
              {saving ? "Saving…" : "Save all to deck…"}
            </Button>
          </div>
        </>
      ) : null}
    </UICard>
  );
}