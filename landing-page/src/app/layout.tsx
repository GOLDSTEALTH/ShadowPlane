import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://shadowplane.vercel.app"),
  title: "ShadowPlane | The Flight Simulator for Terraform",
  description:
    "Intercept broken Terraform configurations, sandbox them in LocalStack, and auto-heal AWS API failures via the autonomous ShadowPatch engine.",
  keywords: [
    "DevOps",
    "CI/CD",
    "Infrastructure as Code",
    "Terraform",
    "AI Auto-Healing",
    "LocalStack",
    "Platform Engineering"
  ],
  openGraph: {
    type: "website",
    url: "https://shadowplane.vercel.app",
    title: "ShadowPlane | The Flight Simulator for Terraform",
    description:
      "Intercept broken Terraform configurations, sandbox them in LocalStack, and auto-heal AWS API failures via the autonomous ShadowPatch engine.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "ShadowPlane Platform",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "ShadowPlane | The Flight Simulator for Terraform",
    description:
      "Intercept broken Terraform configurations, sandbox them in LocalStack, and auto-heal AWS API failures via the autonomous ShadowPatch engine.",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "ShadowPlane",
    applicationCategory: "DeveloperApplication",
    operatingSystem: "Web, Docker, Linux",
    description:
      "The Flight Simulator for Terraform. An enterprise-grade CI/CD policy engine that intercepts broken Terraform configurations, sandboxes them in LocalStack, and auto-heals AWS API failures via the autonomous ShadowPatch engine.",
  };

  return (
    <html lang="en" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans`}>
        {children}
      </body>
    </html>
  );
}
