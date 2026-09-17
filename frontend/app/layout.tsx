import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "@/components/toaster";
import { Providers } from "@/components/providers";
import "@/styles/globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LeadPilot",
  description: "Prospection commerciale B2B enrichie par IA.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" className={`${inter.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-primary text-primary">
        <Providers>
          {children}
          <Toaster position="bottom-right" />
        </Providers>
      </body>
    </html>
  );
}
