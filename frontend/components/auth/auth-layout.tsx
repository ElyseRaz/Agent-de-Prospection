import Link from "next/link";
import { ArrowLeft, CheckCircle } from "@untitledui/icons";
import { BackgroundPattern } from "@/components/shared-assets/background-patterns";

const PRINCIPLES = [
  "Aucune collecte de masse : ajout manuel ou import CSV.",
  "Traçabilité obligatoire sur chaque contact.",
  "Désinscription obligatoire, limite d'envoi quotidienne.",
];

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-primary">
      <aside className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-brand-section p-10 lg:flex">
        <div className="pointer-events-none absolute inset-0">
          <BackgroundPattern pattern="grid-check" size="md" className="text-white/10 mask-b-from-10%" />
        </div>

        <Link href="/" className="relative text-lg font-semibold tracking-tight text-primary_on-brand">
          LeadPilot
        </Link>

        <div className="relative flex flex-col gap-6">
          <p className="text-display-xs font-semibold tracking-tight text-primary_on-brand">
            Une prospection B2B traçable, respectueuse et enrichie par IA.
          </p>
          <ul className="flex flex-col gap-3">
            {PRINCIPLES.map((principle) => (
              <li key={principle} className="flex items-start gap-2.5 text-sm text-secondary_on-brand">
                <CheckCircle className="mt-0.5 size-5 shrink-0 text-primary_on-brand" />
                {principle}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-quaternary_on-brand">
          © {new Date().getFullYear()} LeadPilot. Tous droits réservés.
        </p>
      </aside>

      <div className="flex w-full flex-col lg:w-1/2">
        <div className="flex items-center justify-between p-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/leadpilot.svg" alt="LeadPilot" className="h-7 w-auto lg:hidden" />
          <Link
            href="/"
            className="ml-auto flex items-center gap-1.5 text-sm font-medium text-tertiary hover:text-primary"
          >
            <ArrowLeft className="size-4" />
            Retour à l&apos;accueil
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center px-4 pb-16">
          <div className="w-full max-w-sm">
            <h1 className="text-xl font-semibold text-primary">{title}</h1>
            <p className="mt-1 text-sm text-tertiary">{subtitle}</p>

            <div className="mt-6">{children}</div>

            <p className="mt-6 text-center text-sm text-tertiary">{footer}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
