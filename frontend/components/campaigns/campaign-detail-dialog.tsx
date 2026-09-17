"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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

const MAX_POLL_DURATION_MS = 30_000;

const RECIPIENT_STATUS_CLASS: Record<RecipientStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  sent: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  failed: "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300",
  unsubscribed: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
};

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

  // Une campagne "sending" avance via le worker en tache de fond : on
  // reinterroge jusqu'a ce qu'elle sorte de cet etat (sent ou revenue en
  // draft si la limite quotidienne a ete atteinte).
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
    <Dialog open={Boolean(id)} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {campaign?.name ?? "Campagne"}
            {campaign && <CampaignStatusBadge status={campaign.status} />}
          </DialogTitle>
        </DialogHeader>

        {isLoading || !campaign ? (
          <div className="flex justify-center py-8">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-2 rounded-md border p-3 text-sm">
              <p>
                <span className="font-medium">Objet : </span>
                {campaign.subject}
              </p>
              <p className="whitespace-pre-wrap text-muted-foreground">{campaign.body}</p>
            </div>

            <div className="flex flex-wrap gap-2">
              {Object.entries(campaign.summary).map(([status, count]) => (
                <Badge key={status} variant="outline">
                  {RECIPIENT_STATUS_LABEL[status as RecipientStatus] ?? status} : {count}
                </Badge>
              ))}
            </div>

            <Separator />

            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">
                Destinataires ({campaign.recipients.length})
              </p>
              <div className="max-h-72 overflow-y-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Entreprise</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Statut</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {campaign.recipients.map((recipient) => (
                      <TableRow key={recipient.id}>
                        <TableCell className="font-medium">{recipient.company_name}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {recipient.contact_name ?? recipient.contact_email}
                        </TableCell>
                        <TableCell>
                          <Badge className={RECIPIENT_STATUS_CLASS[recipient.status]}>
                            {RECIPIENT_STATUS_LABEL[recipient.status]}
                          </Badge>
                          {recipient.error_message && (
                            <p className="mt-1 text-xs text-destructive">{recipient.error_message}</p>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>

            <DialogFooter className="justify-between sm:justify-between">
              <Button
                type="button"
                variant="destructive"
                onClick={handleDelete}
                disabled={deleteCampaign.isPending || campaign.status === "sending"}
              >
                <Trash2 className="size-4" />
                Supprimer
              </Button>
              <Button
                type="button"
                onClick={handleSend}
                disabled={sendCampaign.isPending || campaign.status !== "draft"}
              >
                {sendCampaign.isPending || campaign.status === "sending" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Send className="size-4" />
                )}
                {campaign.status === "sent"
                  ? "Deja envoyee"
                  : campaign.status === "sending"
                    ? "Envoi en cours..."
                    : "Envoyer"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
