import type { ApplicationStage } from "../../api/types";

export const STAGE_ORDER: ApplicationStage[] = [
  "spotted",
  "to_apply",
  "applied",
  "in_discussion",
  "proposal",
  "won",
  "lost",
];

export const STAGE_LABELS: Record<ApplicationStage, string> = {
  spotted: "Repere",
  to_apply: "A postuler",
  applied: "Postule",
  in_discussion: "En discussion",
  proposal: "Proposition",
  won: "Gagne",
  lost: "Perdu",
};
