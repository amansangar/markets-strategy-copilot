import type { Metadata } from "next";
import { IBM_Plex_Mono, Space_Grotesk } from "next/font/google";
import { CommandPalette } from "@/components/command-palette";
import { OfflineModeBanner } from "@/components/offline-mode-banner";
import "./globals.css";

const headingFont = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin"],
});

const monoFont = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Markets Strategy Copilot",
  description: "Premium local-first markets research and signal workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${headingFont.variable} ${monoFont.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[radial-gradient(circle_at_top_left,#17355a,transparent_30%),radial-gradient(circle_at_top_right,#0f4f4a,transparent_24%),linear-gradient(180deg,#050811,#09111f_58%,#060910)] text-slate-100">
        <OfflineModeBanner />
        <CommandPalette />
        {children}
      </body>
    </html>
  );
}
