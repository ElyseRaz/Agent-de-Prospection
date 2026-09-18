"use client";

import type { FC } from "react";
import { AlertTriangle } from "@untitledui/icons";
import { Button } from "@/components/base/buttons/button";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";

interface ConfirmDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  icon?: FC<{ className?: string }>;
}

/** Modale de confirmation stylee, a utiliser a la place de window.confirm()
 * pour toute action destructive ou irreversible (suppression, envoi, deconnexion). */
export function ConfirmDialog({
  isOpen,
  onOpenChange,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirmer",
  cancelLabel = "Annuler",
  isDestructive = true,
  isLoading = false,
  icon: Icon = AlertTriangle,
}: ConfirmDialogProps) {
  return (
    <ModalOverlay isOpen={isOpen} onOpenChange={isLoading ? undefined : onOpenChange} isDismissable={!isLoading}>
      <Modal className="w-full sm:max-w-sm">
        <Dialog className="p-6 outline-hidden">
          <FeaturedIcon icon={Icon} color={isDestructive ? "error" : "warning"} theme="light" size="lg" />
          <h2 className="mt-4 text-lg font-semibold text-primary">{title}</h2>
          <p className="mt-1 text-sm text-tertiary">{description}</p>
          <div className="mt-6 flex justify-end gap-3">
            <Button type="button" color="secondary" isDisabled={isLoading} onClick={() => onOpenChange(false)}>
              {cancelLabel}
            </Button>
            <Button
              type="button"
              color={isDestructive ? "primary-destructive" : "primary"}
              isLoading={isLoading}
              onClick={onConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
