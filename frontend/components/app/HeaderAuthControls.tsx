"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import LoginModal from "@/components/auth/LoginModal";

export default function HeaderAuthControls() {
  const [open, setOpen] = React.useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)} className="px-3 py-1.5 text-sm">
        Log in
      </Button>
      <LoginModal open={open} onOpenChange={setOpen} />
    </>
  );
}
