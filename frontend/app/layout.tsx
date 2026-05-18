import type { Metadata } from "next";
import { Geist } from "next/font/google";
import NavBar from "@/components/layout/NavBar";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });

export const metadata: Metadata = {
  title: "PDF RAG — Ask your documents",
  description: "Upload PDFs and ask questions with AI-powered answers and source citations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geist.variable} h-full`}>
      <body className="flex h-full flex-col bg-gray-50 font-sans antialiased">
        <NavBar />
        <div className="flex flex-1 flex-col">{children}</div>
      </body>
    </html>
  );
}
