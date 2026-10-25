import { Navigation } from "@/components/Navigation";

export const metadata = {
  title: "CareerTwin — Application",
};

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full w-full">
      <Navigation />
      <main className="flex-1 min-w-0 overflow-x-hidden pl-64 pt-6 pb-12">
        {children}
      </main>
    </div>
  );
}
