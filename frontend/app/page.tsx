"use client";

import {
  ArrowRight,
  UserPlus01,
  Stars02,
  Star01,
  Mail01,
  BarChartSquare02,
  ShieldTick,
  CheckCircle,
} from "@untitledui/icons";

import { Button } from "@/components/base/buttons/button";
import { Badge } from "@/components/base/badges/badges";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { BackgroundPattern } from "@/components/shared-assets/background-patterns";
import { Reveal } from "@/components/shared-assets/reveal";
import { useAuthStore } from "@/store/auth-store";

const FEATURES = [
  {
    icon: UserPlus01,
    title: "Ajout manuel ou import CSV",
    description:
      "Aucune collecte de masse : chaque entreprise est ajoutée une à une ou importée par toi, jamais aspirée automatiquement.",
  },
  {
    icon: Stars02,
    title: "Enrichissement IA",
    description:
      "Note et avis Trustpilot par domaine, analyse IA de la page d'accueil publique pour détecter des besoins concrets.",
  },
  {
    icon: Mail01,
    title: "Campagnes email",
    description:
      "Éditeur de template, envoi SMTP, lien de désinscription obligatoire et limite d'envoi quotidienne.",
  },
  {
    icon: BarChartSquare02,
    title: "Suivi Kanban",
    description: "Fais glisser chaque prospect entre contacté, répondu et converti pour piloter ton pipeline.",
  },
];

const STEPS = [
  {
    number: "1",
    title: "Ajoute tes prospects",
    description: "Une entreprise à la fois, ou par import CSV, avec une source de contact traçable.",
  },
  {
    number: "2",
    title: "Enrichis chaque fiche",
    description: "Trustpilot et analyse IA du site viennent compléter la fiche existante, jamais la construire.",
  },
  {
    number: "3",
    title: "Lance ta campagne",
    description: "Envoie une proposition ciblée, avec désinscription et limite quotidienne respectées.",
  },
];

const PRINCIPLES = [
  "Aucune collecte de masse : ajout manuel ou import CSV uniquement.",
  "Traçabilité obligatoire : une source_note sur chaque contact.",
  "Trustpilot en enrichissement, jamais en source de prospection.",
  "Désinscription obligatoire et limite d'envoi quotidienne.",
];

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="relative py-1 after:absolute after:-bottom-0.5 after:left-0 after:h-px after:w-0 after:bg-fg-brand-primary after:transition-all after:duration-200 hover:text-primary hover:after:w-full"
    >
      {children}
    </a>
  );
}

export default function LandingPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const isAuthenticated = Boolean(accessToken);

  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-primary">
      <header className="sticky top-0 z-20 border-b border-secondary bg-primary/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/leadpilot.svg" alt="LeadPilot" className="h-7 w-auto" />
          <nav className="hidden items-center gap-6 text-sm font-medium text-tertiary sm:flex">
            <NavLink href="#fonctionnalites">Fonctionnalités</NavLink>
            <NavLink href="#comment-ca-marche">Comment ça marche</NavLink>
            <NavLink href="#principes">Principes</NavLink>
          </nav>
          <div className="flex items-center gap-2">
            {isAuthenticated ? (
              <Button color="primary" size="sm" href="/dashboard" iconTrailing={ArrowRight}>
                Tableau de bord
              </Button>
            ) : (
              <>
                <Button color="tertiary" size="sm" href="/login">
                  Se connecter
                </Button>
                <Button color="primary" size="sm" href="/register">
                  Créer un compte
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 flex justify-center">
            <BackgroundPattern
              pattern="grid-check"
              size="md"
              className="mt-[-80px] text-utility-brand-100 opacity-60 mask-b-from-10%"
            />
          </div>
          <div
            aria-hidden
            className="pointer-events-none absolute -top-24 -left-24 -z-10 size-96 animate-pulse rounded-full bg-utility-brand-200/40 blur-3xl [animation-duration:7s]"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute top-10 -right-32 -z-10 size-[28rem] animate-pulse rounded-full bg-utility-blue-200/40 blur-3xl [animation-duration:9s]"
          />

          <div className="mx-auto flex max-w-4xl flex-col items-center gap-6 px-4 py-20 text-center sm:px-6 sm:py-28">
            <Reveal>
              <Badge color="brand" size="lg" className="gap-2">
                <span className="relative flex size-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-utility-brand-500 opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-utility-brand-600" />
                </span>
                CRM de prospection B2B enrichi par IA
              </Badge>
            </Reveal>
            <Reveal delay={100}>
              <h1 className="text-display-md font-semibold tracking-tight text-primary sm:text-display-lg">
                Prospecte{" "}
                <span className="bg-linear-to-r from-utility-brand-600 to-utility-blue-500 bg-clip-text text-transparent">
                  sans acheter de fichiers, sans scraper le web
                </span>
                .
              </h1>
            </Reveal>
            <Reveal delay={200}>
              <p className="max-w-2xl text-lg text-tertiary">
                Ajoute tes entreprises une à une ou par CSV, laisse l&apos;IA enrichir chaque fiche
                (Trustpilot, analyse de site) et automatise tes campagnes email de proposition de
                services — avec traçabilité et désinscription obligatoires.
              </p>
            </Reveal>
            <Reveal delay={300} className="flex flex-col gap-3 sm:flex-row">
              <Button
                color="primary"
                size="xl"
                href={isAuthenticated ? "/dashboard" : "/register"}
                iconTrailing={ArrowRight}
                className="transition-transform hover:scale-[1.03]"
              >
                {isAuthenticated ? "Aller au tableau de bord" : "Commencer gratuitement"}
              </Button>
              <Button color="secondary" size="xl" href="#fonctionnalites">
                Découvrir les fonctionnalités
              </Button>
            </Reveal>
          </div>
        </section>

        <section id="fonctionnalites" className="border-t border-secondary bg-secondary/40 py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <Reveal className="mx-auto max-w-2xl text-center">
              <h2 className="text-display-xs font-semibold tracking-tight text-primary">
                Tout ce qu&apos;il faut pour prospecter proprement
              </h2>
              <p className="mt-3 text-tertiary">
                Un socle CRM simple, un enrichissement qui complète (jamais qui remplace) ton travail,
                et des campagnes qui respectent tes destinataires.
              </p>
            </Reveal>
            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map((feature, i) => {
                const Icon = feature.icon;
                return (
                  <Reveal
                    key={feature.title}
                    delay={i * 100}
                    className="group flex flex-col gap-4 rounded-2xl bg-primary p-6 shadow-xs ring-1 ring-secondary transition duration-200 hover:-translate-y-1 hover:shadow-lg hover:ring-brand"
                  >
                    <FeaturedIcon
                      icon={Icon}
                      color="brand"
                      theme="light"
                      size="lg"
                      className="transition-transform duration-200 group-hover:scale-110"
                    />
                    <div>
                      <h3 className="text-md font-semibold text-primary">{feature.title}</h3>
                      <p className="mt-1 text-sm text-tertiary">{feature.description}</p>
                    </div>
                  </Reveal>
                );
              })}
            </div>
          </div>
        </section>

        <section id="comment-ca-marche" className="py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <Reveal className="mx-auto max-w-2xl text-center">
              <h2 className="text-display-xs font-semibold tracking-tight text-primary">Comment ça marche</h2>
              <p className="mt-3 text-tertiary">Trois étapes, sans automatisation cachée.</p>
            </Reveal>
            <div className="relative mt-12 grid grid-cols-1 gap-10 sm:grid-cols-3">
              <div
                aria-hidden
                className="absolute top-6 right-[16.5%] left-[16.5%] hidden border-t-2 border-dashed border-secondary sm:block"
              />
              {STEPS.map((step, i) => (
                <Reveal key={step.number} delay={i * 120} className="relative flex flex-col items-center gap-3 text-center sm:items-start sm:text-left">
                  <FeaturedIcon color="brand" theme="dark" size="lg" className="text-md font-bold">
                    {step.number}
                  </FeaturedIcon>
                  <h3 className="text-md font-semibold text-primary">{step.title}</h3>
                  <p className="text-sm text-tertiary">{step.description}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section id="principes" className="border-t border-secondary bg-secondary/40 py-20">
          <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 sm:px-6 lg:grid-cols-2">
            <Reveal>
              <FeaturedIcon icon={ShieldTick} color="success" theme="modern" size="lg" />
              <h2 className="mt-4 text-display-xs font-semibold tracking-tight text-primary">
                Des limites assumées, pas des angles morts
              </h2>
              <p className="mt-3 text-tertiary">
                LeadPilot est construit pour rester une base légale et respectueuse de prospection,
                pas un outil de scraping déguisé.
              </p>
            </Reveal>
            <ul className="flex flex-col gap-4">
              {PRINCIPLES.map((principle, i) => (
                <Reveal
                  key={principle}
                  delay={i * 100}
                  as="li"
                  className="flex items-start gap-3 rounded-xl bg-primary p-4 shadow-xs ring-1 ring-secondary transition duration-200 hover:ring-brand"
                >
                  <CheckCircle className="mt-0.5 size-5 shrink-0 text-fg-success-primary" />
                  <span className="text-sm text-secondary">{principle}</span>
                </Reveal>
              ))}
            </ul>
          </div>
        </section>

        <section className="py-20">
          <Reveal className="relative mx-auto max-w-4xl overflow-hidden rounded-3xl bg-brand-section px-6 py-16 text-center sm:px-16">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 -z-10 opacity-20"
            >
              <BackgroundPattern pattern="grid-check" size="md" className="text-white" />
            </div>
            <div
              aria-hidden
              className="pointer-events-none absolute -bottom-24 -left-16 size-72 animate-pulse rounded-full bg-white/10 blur-3xl [animation-duration:8s]"
            />
            <h2 className="text-display-xs font-semibold tracking-tight text-primary_on-brand">
              Prêt à structurer ta prospection ?
            </h2>
            <p className="mt-3 text-secondary_on-brand">
              Crée un compte et ajoute ta première entreprise en quelques minutes.
            </p>
            <div className="mt-8 flex justify-center">
              <Button
                color="primary"
                size="xl"
                href={isAuthenticated ? "/dashboard" : "/register"}
                iconTrailing={ArrowRight}
                className="transition-transform hover:scale-[1.03]"
              >
                {isAuthenticated ? "Aller au tableau de bord" : "Créer un compte gratuit"}
              </Button>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="border-t border-secondary py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 text-sm text-tertiary sm:flex-row sm:px-6">
          <div className="flex items-center gap-2">
            <Star01 className="size-4" />
            <span>LeadPilot — CRM de prospection B2B</span>
          </div>
          <span>© {new Date().getFullYear()} LeadPilot. Tous droits réservés.</span>
        </div>
      </footer>
    </div>
  );
}
