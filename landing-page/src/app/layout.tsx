import type { Metadata } from "next";
import { IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "ShadowPlane — Autonomous CI/CD Gatekeeper for Terraform",
  description:
    "The flight simulator for Terraform. An agentic DevOps sandbox that intercepts, validates, and self-heals infrastructure before production.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${mono.variable} font-mono`}>{children}</body>
    </html>
  );
}
