import type { Metadata } from "next";
import "./globals.css";
import Providers from "../components/Providers";

export const metadata: Metadata = {
  title: "Wiring Diagram QC Assistant | AI-Powered Compliance SaaS",
  description:
    "Enterprise AI SaaS for automated quality control, discrepancy detection, and regulatory compliance verification of electrical wiring diagram manuals (IPC-WHMA-A-620D, UL 508A).",
  keywords: [
    "Wiring Diagram QC",
    "IPC-WHMA-A-620D",
    "UL 508A",
    "Avionics Harness Inspection",
    "Automated Quality Control",
    "Electrical Schematic AI",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#080c14] text-slate-100 antialiased selection:bg-cyan-500 selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
