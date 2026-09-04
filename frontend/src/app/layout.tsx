import type { Metadata } from "next";
import "./globals.css";

// No next/font/google: the production build must succeed fully offline, so
// the Geist variable names resolve to system stacks defined in globals.css
// (identical rendering chain, zero network fetches at build or runtime).

export const metadata: Metadata = {
  title: "RazorFlow AI — Safe Agentic Commerce",
  description:
    "SprintGear AI buyer with policy-gated approvals, Razorpay test payments, and a merchant console.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
