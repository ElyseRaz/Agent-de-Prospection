"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutAlt01, Users01, BarChartSquare02, Mail01, Settings01, LogOut01 } from "@untitledui/icons";
import { Button as AriaButton } from "react-aria-components";

import { Avatar } from "@/components/base/avatar/avatar";
import { AvatarLabelGroup } from "@/components/base/avatar/avatar-label-group";
import { Dropdown } from "@/components/base/dropdown/dropdown";
import { ConfirmDialog } from "@/components/application/modals/confirm-dialog";
import { useAuthStore } from "@/store/auth-store";
import { cx } from "@/lib/utils/cx";
import { getDisplayName, getInitials } from "@/lib/utils/user-display";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Tableau de bord", icon: LayoutAlt01 },
  { href: "/prospects", label: "Prospects", icon: Users01 },
  { href: "/pipeline", label: "Suivi", icon: BarChartSquare02 },
  { href: "/campaigns", label: "Campagnes", icon: Mail01 },
  { href: "/settings", label: "Parametres", icon: Settings01 },
];

const SIDEBAR_WIDTH = 280;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [confirmLogout, setConfirmLogout] = useState(false);

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="flex min-h-screen">
      <aside
        style={{ "--width": `${SIDEBAR_WIDTH}px` } as React.CSSProperties}
        className="fixed inset-y-0 left-0 z-20 hidden w-(--width) flex-col border-r border-secondary bg-primary pt-5 md:flex"
      >
        <Link href="/dashboard" className="flex items-center gap-2 px-5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/leadpilot.svg" alt="LeadPilot" className="h-8 w-auto" />
        </Link>

        <nav className="flex flex-1 flex-col gap-1 px-4 pt-6">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "flex items-center gap-2.5 rounded-xl p-2.5 text-sm font-semibold transition duration-100 ease-linear",
                  active ? "bg-brand-primary text-brand-secondary" : "text-secondary hover:bg-primary_hover",
                )}
              >
                <Icon className={cx("size-5 shrink-0", active ? "text-fg-brand-primary" : "text-fg-quaternary")} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-secondary p-4">
          <Dropdown.Root>
            <AriaButton className="flex w-full cursor-pointer items-center rounded-lg p-1.5 text-left outline-focus-ring transition duration-100 ease-linear hover:bg-primary_hover focus-visible:outline-2 focus-visible:outline-offset-2">
              <AvatarLabelGroup
                size="sm"
                initials={getInitials(user?.full_name, user?.email)}
                title={getDisplayName(user?.full_name, user?.email)}
                subtitle={user?.email ?? ""}
              />
            </AriaButton>
            <Dropdown.Popover placement="top right" className="w-56">
              <Dropdown.Menu
                onAction={(key) => {
                  if (key === "settings") router.push("/settings");
                  if (key === "logout") setConfirmLogout(true);
                }}
              >
                <Dropdown.Item id="settings" label="Parametres du compte" icon={Settings01} />
                <Dropdown.Separator />
                <Dropdown.Item id="logout" label="Se deconnecter" icon={LogOut01} />
              </Dropdown.Menu>
            </Dropdown.Popover>
          </Dropdown.Root>
        </div>
      </aside>

      <div
        style={{ "--width": `${SIDEBAR_WIDTH}px` } as React.CSSProperties}
        className="flex flex-1 flex-col md:pl-(--width)"
      >
        <header className="flex items-center justify-between border-b border-secondary px-4 py-3 md:hidden">
          <Link href="/dashboard" className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/leadpilot.svg" alt="LeadPilot" className="h-7 w-auto" />
          </Link>
          <Dropdown.Root>
            <AriaButton className="cursor-pointer rounded-full outline-focus-ring focus-visible:outline-2">
              <Avatar
                size="sm"
                initials={getInitials(user?.full_name, user?.email)}
                alt={getDisplayName(user?.full_name, user?.email)}
              />
            </AriaButton>
            <Dropdown.Popover placement="bottom right" className="w-56">
              <Dropdown.Menu
                onAction={(key) => {
                  if (key === "settings") router.push("/settings");
                  if (key === "logout") setConfirmLogout(true);
                }}
              >
                <Dropdown.Item id="settings" label="Parametres du compte" icon={Settings01} />
                <Dropdown.Separator />
                <Dropdown.Item id="logout" label="Se deconnecter" icon={LogOut01} />
              </Dropdown.Menu>
            </Dropdown.Popover>
          </Dropdown.Root>
        </header>
        <main className="flex-1 bg-secondary p-6 lg:p-8">{children}</main>
      </div>

      <ConfirmDialog
        isOpen={confirmLogout}
        onOpenChange={setConfirmLogout}
        onConfirm={handleLogout}
        isDestructive={false}
        icon={LogOut01}
        title="Se deconnecter ?"
        description={`Tu seras deconnecte de ${getDisplayName(user?.full_name, user?.email)} (${user?.email ?? ""}).`}
        confirmLabel="Se deconnecter"
      />
    </div>
  );
}
