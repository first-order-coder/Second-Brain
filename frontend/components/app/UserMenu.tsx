"use client";

import * as React from "react";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

type UserMenuProps = {
  email: string | null;
  name?: string | null;
  imageUrl?: string | null;
};

export default function UserMenu({ email, name, imageUrl }: UserMenuProps) {
  const displayName = name || email || "User";
  const initial = React.useMemo(
    () => (displayName ? displayName.charAt(0).toUpperCase() : "?"),
    [displayName],
  );
  const signOutFormId = React.useId();

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <Avatar className="h-9 w-9">
              <AvatarImage
                src={imageUrl ?? undefined}
                alt={displayName ?? "User avatar"}
              />
              <AvatarFallback>{initial}</AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="truncate">
            {displayName}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/saved">My Decks</Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/profile">Profile</Link>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onSelect={(event) => {
              event.preventDefault();
              try {
                const form = document.getElementById(
                  signOutFormId,
                ) as HTMLFormElement | null;
                if (form) {
                  form.requestSubmit();
                } else {
                  // Fallback: create and submit form programmatically
                  const fallbackForm = document.createElement("form");
                  fallbackForm.method = "post";
                  fallbackForm.action = "/auth/signout";
                  document.body.appendChild(fallbackForm);
                  fallbackForm.submit();
                }
              } catch (error) {
                // Fallback: if form submission fails, create and submit form
                console.error("[UserMenu] Sign out form error:", error);
                try {
                  const fallbackForm = document.createElement("form");
                  fallbackForm.method = "post";
                  fallbackForm.action = "/auth/signout";
                  document.body.appendChild(fallbackForm);
                  fallbackForm.submit();
                } catch (fallbackError) {
                  console.error("[UserMenu] Fallback sign out failed:", fallbackError);
                }
              }
            }}
          >
            <span className="w-full text-left">Sign out</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <form
        id={signOutFormId}
        action="/auth/signout"
        method="post"
        className="hidden"
      />
    </>
  );
}
