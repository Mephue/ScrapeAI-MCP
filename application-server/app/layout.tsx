import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Compare",
  description: "Compare supermarket offers and fuel prices from scraped data.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

