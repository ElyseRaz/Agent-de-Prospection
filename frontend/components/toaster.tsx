"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";
import { CheckCircle, XCircle, AlertTriangle, InfoCircle } from "@untitledui/icons";

export function Toaster(props: ToasterProps) {
  return (
    <Sonner
      className="toaster group"
      icons={{
        success: <CheckCircle className="size-4 text-utility-green-500" />,
        error: <XCircle className="size-4 text-utility-red-500" />,
        warning: <AlertTriangle className="size-4 text-utility-yellow-500" />,
        info: <InfoCircle className="size-4 text-utility-blue-500" />,
      }}
      toastOptions={{
        classNames: {
          toast: "!bg-primary !text-primary !border-secondary !shadow-lg",
          success: "!bg-utility-green-50 !text-utility-green-700 !border-utility-green-200",
          error: "!bg-utility-red-50 !text-utility-red-700 !border-utility-red-200",
          warning: "!bg-utility-yellow-50 !text-utility-yellow-700 !border-utility-yellow-200",
          info: "!bg-utility-blue-50 !text-utility-blue-700 !border-utility-blue-200",
        },
      }}
      {...props}
    />
  );
}
