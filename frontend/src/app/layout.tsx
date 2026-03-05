import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
});

export const metadata: Metadata = {
  title: "Sneak — Market Intelligence Platform",
  description:
    "Real-time competitive intelligence across PR, podcasts, social media, financials, product roadmaps, ads, and influencer activity. Built for teams that move fast.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${jakarta.variable} font-sans min-h-screen bg-[#06060a] text-zinc-50 antialiased`}
        style={{ fontFamily: "var(--font-jakarta), system-ui, sans-serif" }}
      >
        {children}
      </body>
    </html>
  );
}
