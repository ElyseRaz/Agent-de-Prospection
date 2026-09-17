"use client";

import { useEffect, useRef, useState } from "react";
import { Send01, Trash01, X } from "@untitledui/icons";
import { toast } from "sonner";

import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { Badge } from "@/components/base/badges/badges";
import type { BadgeColor } from "@/components/base/badges/badges";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { CampaignStatusBadge } from "@/components/campaigns/campaign-status-badge";
import { useCampaign, useDeleteCampaign, useSendCampaign } from "@/hooks/use-campaigns";
import type { RecipientStatus } from "@/lib/campaigns-api";
import { ApiError } from "@/lib/api";

const RECIPIENT_STATUS_LABEL: Record<RecipientStatus, string> = {
  pending: "En attente",
  sent: "Envoye",
  failed: "Echec",
  unsubscribed: "Desinscrit",
};

const RECIPIENT_STATUS_COLOR: Record<RecipientStatus, BadgeColor<"pill-color">> = {
  pending: "gray",
  sent: "success",
  failed: "error",
  unsubscribed: "warning",
};

const MAX_POLL_DURATION_MS = 30_000;

interface CampaignDetailDialogProps {
  id: string | null;
  onOpenChange: (open: boolean) => void;
}

export function CampaignDetailDialog({ id, onOpenChange }: CampaignDetailDialogProps) {
  const [isPolling, setIsPolling] = useState(false);
  const { data: campaign, isLoading } = useCampaign(id, { poll: isPolling });
  const sendCampaign = useSendCampaign(id ?? "");
  const deleteCampaign = useDeleteCampaign();
  const sendInFlightRef = useRef(false);

  useEffect(() => {
    if (!isPolling || !campaign) return;
    if (sendInFlightRef.current && campaign.status !== "sending") {
      sendInFlightRef.current = false;
      setIsPolling(false);
      toast.success(campaign.status === "sent" ? "Campagne envoyee" : "Envoi termine (voir le detail)");
    }
  }, [isPolling, campaign]);

  const handleSend = async () => {
    if (!campaign) return;
    if (
      !window.confirm(
        `Envoyer "${campaign.name}" a ${campaign.recipients.length} destinataire(s) maintenant ?`,
      )
    ) {
      return;
    }
    try {
      await sendCampaign.mutateAsync();
      toast.info("Envoi lance");
      sendInFlightRef.current = true;
      setIsPolling(true);
      setTimeout(() => setIsPolling(false), MAX_POLL_DURATION_MS);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors du lancement de l'envoi");
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    if (!window.confirm("Supprimer definitivement cette campagne ?")) return;
    try {
      await deleteCampaign.mutateAsync(id);
      toast.success("Campagne supprimee");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de la suppression");
    }
  };

  return (
    <ModalOverlay isOpen={Boolean(id)} onOpenChange={onOpenChange}>
      <Modal className="w-full sm:max-w-2xl">
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
              <h2 className="flex items-center gap-2 text-lg font-semibold text-primary">
                {campaign?.name ?? "Campagne"}
                {campaign && <CampaignStatusBadge status={campaign.status} />}
              </h2>

              {isLoading || !campaign ? (
            <div className="flex justify-center py-8">
              <LoadingIndicator size="sm" />
            </div>
          ) : (
            <>
              <div className="mt-5 flex flex-col gap-2 rounded-md bg-secondary p-3 text-sm">
                <p className="text-secondary">
                  <span className="font-medium">Objet : </span>
                  {campaign.subject}
                </p>
                <p className="whitespace-pre-wrap text-tertiary">{campaign.body}</p>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(campaign.summary).map(([status, count]) => (
                  <Badge key={status} color={RECIPIENT_STATUS_COLOR[status as RecipientStatus] ?? "gray"}>
                    {RECIPIENT_STATUS_LABEL[status as RecipientStatus] ?? status} : {count}
                  </Badge>
                ))}
              </div>

              <hr className="my-5 border-secondary" />

              <div className="flex flex-col gap-2">
                <p className="text-sm font-medium text-secondary">
                  Destinataires ({campaign.recipients.length})
                </p>
                <div className="max-h-72 overflow-y-auto rounded-md ring-1 ring-secondary">
                  <table className="w-full">
                    <thead className="h-9 bg-secondary">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-quaternary">Entreprise</th>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-quaternary">Contact</th>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-quaternary">Statut</th>
                      </tr>
                    </thead>
                    <tbody>
                      {campaign.recipients.map((recipient) => (
                        <tr key={recipient.id} className="border-t border-secondary">
                          <td className="px-4 py-3 text-sm font-medium text-primary">{recipient.company_name}</td>
                          <td className="px-4 py-3 text-sm text-tertiary">
                            {recipient.contact_name ?? recipient.contact_email}
                          </td>
                          <td className="px-4 py-3">
                            <Badge color={RECIPIENT_STATUS_COLOR[recipient.status]}>
                              {RECIPIENT_STATUS_LABEL[recipient.status]}
                            </Badge>
                            {recipient.error_message && (
                              <p className="mt-1 text-xs text-error-primary">{recipient.error_message}</p>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="mt-5 flex justify-between">
                <Button
                  type="button"
                  color="secondary-destructive"
                  iconLeading={Trash01}
                  isLoading={deleteCampaign.isPending}
                  isDisabled={campaign.status === "sending"}
                  onClick={handleDelete}
                >
                  Supprimer
                </Button>
                <Button
                  type="button"
                  iconLeading={Send01}
                  isLoading={sendCampaign.isPending || campaign.status === "sending"}
                  isDisabled={campaign.status !== "draft"}
                  onClick={handleSend}
                >
                  {campaign.status === "sent"
                    ? "Deja envoyee"
                    : campaign.status === "sending"
                      ? "Envoi en cours..."
                      : "Envoyer"}
                </Button>
              </div>
                </>
              )}
            </>
          )}
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
