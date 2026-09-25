import type { Metadata } from "next";
import "./globals.css";
import Providers from "../components/Providers";

export const metadata: Metadata = {
  title: "Wiring Diagram QC Assistant | Automated AI Quality Control",
  description:
    "Enterprise AI SaaS for automated quality control, discrepancy detection, and regulatory compliance verification of electrical wiring diagram manuals (IPC-WHMA-A-620D, UL 508A).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className="min-h-screen bg-slate-50 text-slate-900 antialiased selection:bg-blue-600 selection:text-white"
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
