"use client";

import { useState, useMemo } from "react";
import { usePathname } from "next/navigation";
import { MessageCircle } from "lucide-react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type Status = "idle" | "loading" | "success" | "error";

/**
 * Floating feedback button + dialog.
 *
 * Allows users to send quick feedback that is stored in Supabase via
 * the `/api/feedback` route. This component is self-contained and does
 * not touch any PDF / YouTube / deck logic.
 */
export function FeedbackButton() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorText, setErrorText] = useState<string | null>(null);

  const isSendDisabled = useMemo(
    () => status === "loading" || message.trim().length < 5,
    [status, message]
  );

  const resolvePageUrl = () => {
    if (typeof window !== "undefined" && window.location?.href) {
      return window.location.href;
    }
    return pathname || "/";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedMessage = message.trim();
    if (trimmedMessage.length < 5) {
      setErrorText("Please provide a bit more detail (at least 5 characters).");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setErrorText(null);

    try {
      const pageUrl = resolvePageUrl();
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmedMessage,
          email: email.trim() || undefined,
          pageUrl,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const msg =
          typeof data?.error === "string"
            ? data.error
            : "Failed to send feedback. Please try again.";
        setErrorText(msg);
        setStatus("error");
        return;
      }

      setStatus("success");
      setMessage("");
      // Keep email so users don't need to retype on subsequent feedback
    } catch (err) {
      console.error("[FeedbackButton] Failed to send feedback:", err);
      setErrorText("Network error while sending feedback. Please try again.");
      setStatus("error");
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-40">
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button
            size="sm"
            className="shadow-md rounded-full flex items-center gap-1.5"
            variant="default"
          >
            <MessageCircle className="h-4 w-4" />
            <span className="hidden sm:inline">Feedback</span>
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send feedback</DialogTitle>
            <DialogDescription>
              Share bugs, ideas, or anything that would make Second Brain more
              useful for you.
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label
                htmlFor="feedback-message"
                className="text-sm font-medium text-foreground"
              >
                Your feedback
              </label>
              <textarea
                id="feedback-message"
                required
                minLength={5}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y"
                placeholder="Tell us what worked well, what broke, or what you'd like to see next."
              />
              <p className="text-xs text-muted-foreground">
                Please avoid sharing sensitive information. We use this feedback
                to improve the product.
              </p>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="feedback-email"
                className="text-sm font-medium text-foreground"
              >
                Email (optional)
              </label>
              <Input
                id="feedback-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
              <p className="text-xs text-muted-foreground">
                Only used if we need to follow up. Leave blank to stay
                anonymous.
              </p>
            </div>

            {errorText && (
              <p className="text-xs text-red-600">{errorText}</p>
            )}
            {status === "success" && (
              <p className="text-xs text-emerald-600">
                Thank you! Your feedback has been sent.
              </p>
            )}

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setOpen(false);
                  setStatus("idle");
                  setErrorText(null);
                }}
              >
                Close
              </Button>
              <Button type="submit" disabled={isSendDisabled}>
                {status === "loading" ? "Sending…" : "Send"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}


