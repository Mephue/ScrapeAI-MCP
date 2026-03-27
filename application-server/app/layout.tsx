import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SmartCart Assist",
  description: "Intelligenter Einkaufsassistent fuer optimierte Supermarkt-Einkaeufe.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}

