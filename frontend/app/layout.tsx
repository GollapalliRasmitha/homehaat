import type { Metadata } from "next";
import { Instrument_Serif, Inter_Tight } from "next/font/google";
import { Toaster } from "sonner";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SessionProvider } from "@/lib/session";

import "./globals.css";

// Fonts are downloaded at build time and served from our own site (no Google requests from the browser).
const interTight = Inter_Tight({ subsets: ["latin"], variable: "--font-inter-tight" });
const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: "italic",
  variable: "--font-instrument-serif",
});

export const metadata: Metadata = {
  title: "HomeHaat · Made at home, made for you",
  description: "Cakes, pickles, art and tailoring from home makers near you. One bag, many makers, one payment.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${interTight.variable} ${instrumentSerif.variable}`}>
      <body className="flex min-h-screen flex-col">
        <SessionProvider>
          <Header />
          <main className="wrap flex-1 pb-20 pt-12">{children}</main>
          <Footer />
          {/* UI-UX.md: toast is a black pill at the bottom centre */}
          <Toaster
            position="bottom-center"
            toastOptions={{
              unstyled: true,
              className: "rounded-full bg-ink px-5 py-3 text-[14.5px] font-medium text-white shadow-lg",
            }}
          />
        </SessionProvider>
      </body>
    </html>
  );
}
