"use client";

import { useRef, useState } from "react";
import { Loader2, Upload } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useImportProspects } from "@/hooks/use-prospects";
import { ApiError } from "@/lib/api";
import type { ImportResponse } from "@/lib/prospects-api";

export function ImportDialog() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const importProspects = useImportProspects();

  const handleImport = async () => {
    if (!file) return;
    try {
      const response = await importProspects.mutateAsync(file);
      setResult(response);
      if (response.imported > 0) {
        toast.success(`${response.imported} prospect(s) importe(s)`);
      }
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de l'import");
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setFile(null);
          setResult(null);
          if (inputRef.current) inputRef.current.value = "";
        }
      }}
    >
      <DialogTrigger render={<Button variant="outline"><Upload className="size-4" />Importer un CSV</Button>} />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Importer des prospects (CSV)</DialogTitle>
          <DialogDescription>
            Colonnes attendues : <code>name,domain,email,source_note</code>. <code>source_note</code>{" "}
            devient obligatoire des qu&apos;un email est fourni sur la ligne.
          </DialogDescription>
        </DialogHeader>

        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
          }}
          className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium"
        />

        {result && (
          <div className="rounded-md border bg-muted/50 p-3 text-sm">
            <p className="font-medium">
              {result.imported} importe(s), {result.skipped} ignore(s)
            </p>
            {result.rows.filter((r) => r.status === "error").length > 0 && (
              <ul className="mt-2 max-h-32 list-disc space-y-0.5 overflow-y-auto pl-4 text-xs text-muted-foreground">
                {result.rows
                  .filter((r) => r.status === "error")
                  .map((r) => (
                    <li key={r.row}>
                      Ligne {r.row} : {r.message}
                    </li>
                  ))}
              </ul>
            )}
          </div>
        )}

        <DialogFooter>
          <Button onClick={handleImport} disabled={!file || importProspects.isPending}>
            {importProspects.isPending ? <Loader2 className="size-4 animate-spin" /> : "Importer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
