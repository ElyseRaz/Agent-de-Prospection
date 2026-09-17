"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

export function Toaster(props: ToasterProps) {
  return (
    <Sonner
      className="toaster group"
      toastOptions={{
        classNames: {
          toast: "!bg-primary !text-primary !border-secondary !shadow-lg",
        },
      }}
      {...props}
    />
  );
}
