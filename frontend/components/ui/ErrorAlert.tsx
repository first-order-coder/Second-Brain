"use client";

import * as React from "react";
import { AlertCircle } from "lucide-react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

interface ErrorAlertProps {
  /** Optional title/heading for the error */
  title?: string;
  /** Main error message */
  message: string;
  /** Optional list of next steps or details as bullet points */
  details?: string[];
  /** Additional CSS classes */
  className?: string;
}

/**
 * Reusable error alert component for displaying user-friendly error messages.
 * Uses shadcn/ui Alert primitives for consistent styling.
 */
export function ErrorAlert({ title, message, details, className }: ErrorAlertProps) {
  return (
    <Alert variant="destructive" className={cn("mb-4", className)}>
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title || "Something went wrong"}</AlertTitle>
      <AlertDescription>
        <p className="mb-2">{message}</p>
        {details && details.length > 0 && (
          <ul className="list-disc list-inside space-y-1 text-sm mt-2">
            {details.map((detail, index) => (
              <li key={index}>{detail}</li>
            ))}
          </ul>
        )}
      </AlertDescription>
    </Alert>
  );
}



