"use client";

import { useRef, useState } from "react";
import { UploadCloud01, Download01, X } from "@untitledui/icons";
import { toast } from "sonner";

import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { Dialog, DialogTrigger, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { useImportProspects } from "@/hooks/use-prospects";
import { ApiError } from "@/lib/api";
import { downloadImportTemplate } from "@/lib/prospects-api";
import type { ImportResponse } from "@/lib/prospects-api";

export function ImportDialog() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResponse | null>(null);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
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

  const handleDownloadTemplate = async () => {
    setDownloadingTemplate(true);
    try {
      await downloadImportTemplate();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors du telechargement du modele");
    } finally {
      setDownloadingTemplate(false);
    }
  };

  return (
    <DialogTrigger
      isOpen={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setFile(null);
          setResult(null);
          if (inputRef.current) inputRef.current.value = "";
        }
      }}
    >
      <Button size="md" color="secondary" iconLeading={UploadCloud01}>
        Importer des prospects
      </Button>
      <ModalOverlay>
        <Modal className="w-full sm:max-w-md">
          <Dialog className="relative max-h-[inherit] w-full overflow-y-auto p-6 outline-hidden">
            {({ close }) => (
              <>
                <ButtonUtility
                  size="sm"
                  color="tertiary"
                  icon={X}
                  tooltip="Fermer"
                  onClick={close}
                  className="absolute top-4 right-4"
                />
                <h2 className="text-lg font-semibold text-primary">Importer des prospects (CSV ou Excel)</h2>
                <p className="mt-1 text-sm text-tertiary">
                  Seule la colonne <code>name</code> est obligatoire. Colonnes reconnues :{" "}
                  <code>name, domain, website, address, phone, company_email, email, source_note</code>.{" "}
                  <code>email</code> cree un contact trace ; <code>source_note</code> devient alors
                  obligatoire.
                </p>

                <Button
                  type="button"
                  size="sm"
                  color="link-color"
                  iconLeading={Download01}
                  isLoading={downloadingTemplate}
                  onClick={handleDownloadTemplate}
                  className="mt-3"
                >
                  Telecharger le modele Excel
                </Button>

                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,text/csv,.xlsx,.xlsm,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] ?? null);
                    setResult(null);
                  }}
                  className="mt-4 text-sm text-tertiary file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-secondary"
                />

                {result && (
                  <div className="mt-3 rounded-md bg-secondary p-3 text-sm">
                    <p className="font-medium text-secondary">
                      {result.imported} importe(s), {result.skipped} ignore(s)
                    </p>
                    {result.rows.filter((r) => r.status === "error").length > 0 && (
                      <ul className="mt-2 max-h-32 list-disc space-y-0.5 overflow-y-auto pl-4 text-xs text-tertiary">
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

                <div className="mt-5 flex justify-end gap-3">
                  <Button type="button" size="md" color="secondary" onClick={close}>
                    Annuler
                  </Button>
                  <Button onClick={handleImport} isDisabled={!file} isLoading={importProspects.isPending}>
                    Importer
                  </Button>
                </div>
              </>
            )}
          </Dialog>
        </Modal>
      </ModalOverlay>
    </DialogTrigger>
  );
}
