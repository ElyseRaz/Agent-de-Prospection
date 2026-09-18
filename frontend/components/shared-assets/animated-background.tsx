"use client";

/** Soft blurred gradient blobs that slowly drift and scale in a loop, layered
 * behind page content instead of a flat background color. Respects
 * prefers-reduced-motion via the `motion-safe:` variant. */
export function AnimatedBackground() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-32 -left-32 size-[34rem] rounded-full bg-utility-brand-200/50 blur-3xl motion-safe:animate-[drift-a_24s_ease-in-out_infinite]" />
      <div className="absolute -right-40 top-1/4 size-[30rem] rounded-full bg-utility-blue-200/50 blur-3xl motion-safe:animate-[drift-b_28s_ease-in-out_infinite]" />
      <div className="absolute bottom-[-8rem] left-1/4 size-[28rem] rounded-full bg-utility-brand-300/40 blur-3xl motion-safe:animate-[drift-c_32s_ease-in-out_infinite]" />
      <div className="absolute right-1/4 bottom-1/3 size-[24rem] rounded-full bg-utility-blue-300/30 blur-3xl motion-safe:animate-[drift-a_20s_ease-in-out_infinite_reverse]" />
      <style>{`
        @keyframes drift-a {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(8vw, 10vh) scale(1.15); }
          66% { transform: translate(-5vw, 14vh) scale(0.9); }
        }
        @keyframes drift-b {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(-10vw, 8vh) scale(0.92); }
          66% { transform: translate(-4vw, -10vh) scale(1.1); }
        }
        @keyframes drift-c {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(6vw, -12vh) scale(1.08); }
        }
      `}</style>
    </div>
  );
}
