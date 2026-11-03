import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/nav/Navbar";

export const metadata: Metadata = {
  title: "NFL Analytics",
  description: "NFL analytics: QB performance by personnel matchup (2022–2025) and weekly ANY/A game projections.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-50 min-h-screen">
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
