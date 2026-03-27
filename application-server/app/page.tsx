import { Hero1 } from "@/components/ui/hero-1";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function HomePage() {
  return <Hero1 />;
}

