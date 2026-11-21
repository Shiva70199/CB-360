import Link from "next/link";
import { LayoutShell } from "@/components/LayoutShell";

const features = [
  {
    eyebrow: "Ingest",
    title: "Smart Data Processing",
    detail:
      "Validate POS line items, parse order dates and keep a clear record of every import.",
  },
  {
    eyebrow: "Decisions",
    title: "Business Intelligence",
    detail:
      "Turn transaction history into revenue, order and outlet measures your team can act on.",
  },
  {
    eyebrow: "Explore",
    title: "Interactive Analytics",
    detail:
      "Follow sales, menu items, outlets, order types and payment methods in live charts.",
  },
  {
    eyebrow: "Focus",
    title: "Advanced Filtering",
    detail:
      "Date, brand, outlet, category, order type and settlement update every view together.",
  },
];

export default function LandingPage() {
  return (
    <LayoutShell>
      <section className="relative flex flex-1 flex-col justify-center py-10 sm:py-16">
        <div className="mx-auto w-full max-w-4xl">
          <p className="section-title tracking-[0.3em] text-xs">CB 360</p>
          <h1 className="heading-xl mt-5 max-w-3xl">
            See Your Business from{" "}
            <span className="underline decoration-[0.2em] decoration-emerald-600 underline-offset-4">
              Every Angle.
            </span>
          </h1>
          <p className="mt-5 text-lg font-medium text-slate-800 dark:text-slate-200">
            Your restaurant data, transformed into smarter business decisions.
          </p>
          <p className="muted-copy mt-4 max-w-2xl">
            Explore revenue trends, menu performance, outlet comparisons and
            transaction insights through a unified business intelligence experience.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/register" className="accent-button h-14 px-8 text-center leading-[3.25rem]">
              Get started
            </Link>
            <Link
              href="/login"
              className="inline-flex h-14 items-center justify-center rounded-full border border-slate-300 bg-white px-8 text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
            >
              Log in
            </Link>
          </div>
          <div className="mt-12 grid gap-4 sm:grid-cols-2">
            {features.map((feature) => (
              <div key={feature.title} className="premium-card premium-card-hover p-6">
                <p className="section-title">{feature.eyebrow}</p>
                <p className="mt-3 text-base font-semibold text-slate-900 dark:text-white">
                  {feature.title}
                </p>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{feature.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </LayoutShell>
  );
}
