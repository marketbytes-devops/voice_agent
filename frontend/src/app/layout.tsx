import type { Metadata } from "next";
import { Inter, Noto_Sans_Malayalam } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/layout/AppShell";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const notoSansMalayalam = Noto_Sans_Malayalam({
  subsets: ["malayalam"],
  variable: "--font-noto-malayalam",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "ClinicVoice | Sreerudra Ayurveda Hospital AI Receptionist",
  description: "AI Phone Receptionist & Doctor Appointment Management for Sreerudra Ayurveda Hospital, Alappuzha, Kerala.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${notoSansMalayalam.variable} dark`}>
      <body className="font-sans bg-slate-950 text-slate-100 overflow-hidden">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
