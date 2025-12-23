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
import { apiGet, apiPost, apiPut, ApiError } from "@/lib/apiClient";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { useAuth } from "@/lib/auth";
import LoginModal from "@/components/auth/LoginModal";

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
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [mode, setMode] = useState<"auto" | "manual">("auto"); // Mode selector: Auto or Manual transcript
  const [url, setUrl] = useState("");
  // Fixed 10 cards for YouTube - no count selector needed
  const [allowAuto, setAllowAuto] = useState(true);
  const [useCookies, setUseCookies] = useState(false);
  const [enableFallback, setEnableFallback] = useState(false);
  const [langHint, setLangHint] = useState<string[]>(["en","en-US","en-GB"]);
  const [transcriptText, setTranscriptText] = useState(""); // Manual transcript text
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<string[] | undefined>(undefined);
  const [resp, setResp] = useState<YouTubeFlashcardsResponse | null>(null);
  const [lastDeckId, setLastDeckId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [tracks, setTracks] = useState<{
    video_id: string;
    tracks: Array<{lang: string; kind: string}>;
    gated: boolean;
  } | null>(null);
  const [checkingTracks, setCheckingTracks] = useState(false);

  // Client-side URL cleaning as safeguard
  const cleanYoutubeUrl = useCallback((raw: string): string => {
    const s = raw.trim();
    // Fix duplicated URLs
    if (s.length % 2 === 0) {
      const half = s.length / 2;
      if (s.slice(0, half) === s.slice(half)) {
        return s.slice(0, half);
      }
    }
    return s;
  }, []);

  const saveDeckSilently = useCallback((deckId: string, title: string, sourceLabel: string) => {
    fetch("/api/save-deck", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        deckId,
        title,
        sourceType: "youtube",
        sourceLabel,
      }),
    })
      .then((res) => res.json().catch(() => ({})))
      .then((json) => {
        if (!json?.ok) {
          console.warn("[YTToCards] save-deck failed", { deckId, json });
        } else {
          console.log("[YTToCards] save-deck succeeded", { deckId, title });
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
      const data = await apiGet<{
        video_id: string;
        tracks: Array<{lang: string; kind: string}>;
        gated: boolean;
      }>(`/youtube/tracks?url=${encodeURIComponent(url)}`);
      setTracks(data);
      // Auto-adjust language hints if no English tracks
      const hasEnglish = data.tracks.some((t: any) => t.lang.startsWith('en'));
      if (!hasEnglish && data.tracks.length > 0) {
        const topLang = data.tracks[0].lang;
        setLangHint([topLang, "en"]);
      }
    } catch (err: any) {
      setError(err instanceof Error ? err.message : "Network error checking tracks.");
    } finally {
      setCheckingTracks(false);
    }
  }

  // Helper function to handle successful flashcard generation (shared by auto and manual modes)
  const handleFlashcardSuccess = useCallback((data: YouTubeFlashcardsResponse, cleanedUrl: string) => {
    setResp(data);
    console.log("[YTToCards] Flashcard generation success:", {
      deckId: data.deck_id,
      videoTitle: data.videoTitle || data.title,
      responseUrl: data.url,
    });
    
    // Auto-navigate to deck if deck_id is present (deck parity with PDF flow)
    if (data?.deck_id) {
      setLastDeckId(data.deck_id);
      
      // Use backend-provided videoTitle or title, fallback to video ID
      const finalUrl = data.url ?? cleanedUrl;
      const fallbackTitle = (() => {
        try {
          const u = new URL(finalUrl);
          const v = u.searchParams.get("v");
          if (v) return `YouTube: ${v}`;
        } catch (_) {
          // ignore
        }
        return "YouTube deck";
      })();
      
      const deckTitle = (data.videoTitle || data.title || fallbackTitle).trim();
      
      // CRITICAL: Ensure we always have a non-empty title (never null/empty)
      if (!deckTitle || deckTitle.length === 0) {
        console.error("[YTToCards] No valid title available, using fallback", {
          deckId: data.deck_id,
          videoTitle: data.videoTitle,
          title: data.title,
          fallbackTitle,
        });
        const emergencyFallback = `YouTube: ${data.video_id || data.deck_id.slice(0, 8)}`;
        console.warn("[YTToCards] Using emergency fallback title:", emergencyFallback);
        setError("Failed to get video title. Please try again.");
        return;
      }
      
      console.log("[YTToCards] Using deckTitle:", deckTitle);
      console.log("[YTToCards] Calling saveDeckSilently for YouTube:", {
        deckId: data.deck_id,
        deckTitle,
        sourceType: "youtube",
        sourceLabel: finalUrl,
      });
      
      saveDeckSilently(data.deck_id, deckTitle, finalUrl);
      
      const query = new URLSearchParams({
        title: deckTitle,
        sourceType: "youtube",
        sourceLabel: finalUrl,
      });
      
      router.push(`/flashcards/${data.deck_id}?${query.toString()}`);
    }
  }, [router, saveDeckSilently]);

  async function onGenerate() {
    // Check auth before proceeding
    if (!isAuthenticated) {
      setShowLoginModal(true);
      return;
    }
    
    setLoading(true); 
    setError(null); 
    setResp(null);
    try {
      // Clean URL on client side as safeguard
      const cleanedUrl = cleanYoutubeUrl(url);
      console.log("[YTToCards] Sending request with URL:", cleanedUrl);
      
      // Build payload - fixed 10 cards on server side
      // IMPORTANT: Field names must match backend Pydantic model (snake_case)
      const payload: any = {
        url: cleanedUrl, // Send cleaned URL
        n_cards: 10, // Fixed value, server will enforce 10
        lang_hint: langHint, // Backend expects lang_hint (snake_case), not langHint (camelCase)
        allow_auto_generated: allowAuto,
        use_cookies: useCookies,
        enable_fallback: enableFallback
      };
      
      console.log("[YTToCards] Request payload:", payload);
      
      const data = await apiPost<YouTubeFlashcardsResponse>("/youtube/flashcards", payload);
      handleFlashcardSuccess(data, cleanedUrl);
    } catch (err: any) {
      // Enhanced error logging for 422 and other errors
      console.error("[YTToCards] Error generating flashcards:", err);
      console.error("[YTToCards] Error details (stringified):", JSON.stringify(err, Object.getOwnPropertyNames(err), 2));
      
      // Extract error message and nextSteps from ApiError
      let errorMessage = "Network error or API unavailable.";
      let nextSteps: string[] | undefined = undefined;
      
      if (err instanceof Error) {
        errorMessage = err.message;
        
        // Handle 401 auth errors
        const errorStatus = 'status' in err ? (err as any).status : null;
        if (errorStatus === 401) {
          errorMessage = "Please sign in to generate flashcards.";
          setShowLoginModal(true);
        }
        
        // Check if error has nextSteps (from ApiError)
        if ('nextSteps' in err && Array.isArray(err.nextSteps)) {
          nextSteps = err.nextSteps;
        }
        
        // If no nextSteps from API, check if error suggests manual mode might help
        if (!nextSteps) {
          const errorLower = errorMessage.toLowerCase();
          if (errorLower.includes("no transcript") || 
              (errorLower.includes("transcript") && (errorLower.includes("unavailable") || errorLower.includes("not available"))) ||
              errorLower.includes("blocking") ||
              errorLower.includes("age/consent") ||
              errorLower.includes("restricted")) {
            nextSteps = ["Switch to Manual transcript mode and paste the transcript yourself"];
          }
        }
      } else if (typeof err === 'object' && err !== null) {
        errorMessage = JSON.stringify(err);
      }
      
      setError(errorMessage);
      setErrorDetails(nextSteps);
    } finally {
      setLoading(false);
    }
  }

  async function onGenerateFromTranscript() {
    // Check auth before proceeding
    if (!isAuthenticated) {
      setShowLoginModal(true);
      return;
    }
    
    // Validate transcript text
    const trimmedTranscript = transcriptText.trim();
    if (!trimmedTranscript) {
      setError("Transcript text is empty.");
      setErrorDetails(["Paste or type some content in the transcript textarea before generating"]);
      return;
    }

    setLoading(true);
    setError(null);
    setErrorDetails(undefined);
    setResp(null);
    
    try {
      // Clean URL if provided (optional metadata)
      const cleanedUrl = url ? cleanYoutubeUrl(url) : null;
      
      // Try to extract video title from URL if available
      let videoTitleGuess: string | null = null;
      if (cleanedUrl) {
        try {
          const u = new URL(cleanedUrl);
          const v = u.searchParams.get("v");
          if (v) {
            videoTitleGuess = `YouTube: ${v}`;
          }
        } catch (_) {
          // ignore
        }
      }
      
      const payload = {
        url: cleanedUrl,
        title: videoTitleGuess,
        transcript: trimmedTranscript,
      };
      
      console.log("[YTToCards] Sending manual transcript request:", {
        url: cleanedUrl,
        title: videoTitleGuess,
        transcriptLength: trimmedTranscript.length,
      });
      
      const data = await apiPost<YouTubeFlashcardsResponse>("/youtube/transcript-flashcards", payload);
      handleFlashcardSuccess(data, cleanedUrl || "");
    } catch (err: any) {
      console.error("[YTToCards] Error generating flashcards from transcript:", err);
      console.error("[YTToCards] Error details (stringified):", JSON.stringify(err, Object.getOwnPropertyNames(err), 2));
      
      let errorMessage = "Failed to generate flashcards from transcript.";
      let nextSteps: string[] | undefined = undefined;
      
      if (err instanceof Error) {
        errorMessage = err.message;
        
        // Handle 401 auth errors
        const errorStatus = 'status' in err ? (err as any).status : null;
        if (errorStatus === 401) {
          errorMessage = "Please sign in to generate flashcards.";
          setShowLoginModal(true);
        }
        
        // Check if error has nextSteps (from ApiError)
        if ('nextSteps' in err && Array.isArray(err.nextSteps)) {
          nextSteps = err.nextSteps;
        }
      } else if (typeof err === 'object' && err !== null) {
        errorMessage = JSON.stringify(err);
      }
      
      setError(errorMessage);
      setErrorDetails(nextSteps);
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
      const data = await apiPut<{ pdf_id: string }>("/youtube/save", {
        url: resp.url,
        video_id: resp.video_id,
        title: resp.title,
        lang: resp.lang,
        cards: resp.cards.map(c => ({ front: c.front, back: c.back, cloze: c.cloze, start_s: c.start_s, end_s: c.end_s, evidence: c.evidence, difficulty: c.difficulty, tags: c.tags }))
      });
      // Navigate to viewer for this synthetic deck id
      if (data?.pdf_id) {
        const finalUrl = resp?.url || url;
        const fallbackTitle = (() => {
          try {
            const u = new URL(finalUrl);
            const v = u.searchParams.get("v");
            if (v) return `YouTube: ${v}`;
          } catch (_) {
            // ignore
          }
          return "YouTube deck";
        })();
        const deckTitle = (resp?.videoTitle || resp?.title || fallbackTitle).trim();
        saveDeckSilently(data.pdf_id, deckTitle, finalUrl);
        // Pass all needed params to flashcard page
        const params = new URLSearchParams({
          title: deckTitle,
          sourceType: "youtube",
          sourceLabel: finalUrl,
        });
        window.location.href = `/flashcards/${data.pdf_id}?${params.toString()}`;
      } else {
        window.location.href = "/";
      }
    } catch (err) {
      setError("Network error while saving deck.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <UICard className="p-4 space-y-4">
      {/* Beta notice for YouTube feature - at the top */}
      <div className="text-xs text-muted-foreground italic flex items-start gap-1.5">
        <span className="text-amber-600 dark:text-amber-400">ℹ️</span>
        <span>YouTube mode is in beta. Some videos may not work due to YouTube caption restrictions.</span>
      </div>

      {/* Mode selector */}
      <div className="space-y-2">
        <Label>Mode</Label>
        <div className="flex gap-2">
          <Button
            variant={mode === "auto" ? "default" : "outline"}
            onClick={() => setMode("auto")}
            className="flex-1"
          >
            Auto (from YouTube captions)
          </Button>
          <Button
            variant={mode === "manual" ? "default" : "outline"}
            onClick={() => setMode("manual")}
            className="flex-1"
          >
            Manual transcript
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          {mode === "auto" 
            ? "Automatically fetch captions from YouTube and generate flashcards."
            : "Paste transcript text manually when automatic caption fetching fails."}
        </p>
      </div>

      {/* URL input - visible in both modes */}
      <div className="space-y-2">
        <Label htmlFor="yt-url">Paste YouTube URL {mode === "manual" && "(optional)"}</Label>
        <Input
          id="yt-url"
          placeholder="https://youtu.be/VIDEO_ID or https://www.youtube.com/watch?v=VIDEO_ID"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onPaste={onPasteLink}
        />
        <p className="text-xs text-muted-foreground">
          {mode === "auto" 
            ? "Paste a link, then click 'Generate Flashcards'. This will create 10 flashcards."
            : "Optional: Paste the YouTube URL for reference (helps with deck metadata)."}
        </p>
      </div>

      {/* Options section - only show in Auto mode */}
      {mode === "auto" && (
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
      )}

      {/* Manual transcript textarea - only show in Manual mode */}
      {mode === "manual" && (
        <div className="space-y-2">
          <Label htmlFor="transcript-text">Transcript text</Label>
          <textarea
            id="transcript-text"
            className="flex min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y"
            placeholder="Paste the transcript text here. You can copy it from YouTube's transcript feature or any other source."
            value={transcriptText}
            onChange={(e) => setTranscriptText(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Paste the full transcript text. The system will automatically process it and generate 10 flashcards.
          </p>
        </div>
      )}

      <div className="space-y-2">
        <div className="flex gap-2">
          {mode === "auto" ? (
            <>
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
            </>
          ) : (
            <Button 
              onClick={onGenerateFromTranscript} 
              disabled={!transcriptText.trim() || loading}
              className="w-full"
            >
              {loading ? "Generating…" : "Generate from transcript"}
            </Button>
          )}
        </div>
        {mode === "auto" && (
          <p className="text-xs text-muted-foreground">
            YouTube generation creates <span className="font-medium">10</span> flashcards by default.
            (Count control removed for MVP reliability.)
          </p>
        )}
        {error && (
          <ErrorAlert
            title={mode === "auto" ? "Couldn't generate flashcards" : "Transcript processing failed"}
            message={error}
            details={errorDetails}
          />
        )}
        
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
      
      {/* Auth prompt for unauthenticated users */}
      {!isAuthenticated && !authLoading && (
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-center">
          <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">
            Sign in to generate flashcards from YouTube videos
          </p>
          <Button 
            variant="default" 
            onClick={() => setShowLoginModal(true)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            Sign in
          </Button>
        </div>
      )}
      
      {/* Login Modal */}
      <LoginModal open={showLoginModal} onOpenChange={setShowLoginModal} />
    </UICard>
  );
}