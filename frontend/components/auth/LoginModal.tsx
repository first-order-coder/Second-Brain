"use client";

import * as React from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

interface LoginModalProps {
  open: boolean;
  onOpenChange: (value: boolean) => void;
}

export default function LoginModal({ open, onOpenChange }: LoginModalProps) {
  const supabase = createClient();

  async function onGoogle() {
    const base = process.env.NEXT_PUBLIC_APP_URL || window.location.origin;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${base}/auth/callback` },
    });
    if (error) {
      alert(error.message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Log in or sign up</DialogTitle>
          <DialogDescription>
            Use your Google account to save decks and access them later.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-3">
          <Button onClick={onGoogle} className="w-full">
            Continue with Google
          </Button>
        </div>

        <p className="mt-3 text-xs text-muted-foreground">
          By continuing, you agree to our Terms and Privacy Policy.
        </p>
      </DialogContent>
    </Dialog>
  );
}
