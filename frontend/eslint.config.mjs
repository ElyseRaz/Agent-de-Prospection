import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Vendored Untitled UI components/hooks (installed via `npx untitledui add`,
    // never hand-edited - re-vendored wholesale on `untitledui upgrade`).
    "components/base/**",
    "components/application/**",
    "components/foundations/**",
    "components/shared-assets/**",
    "hooks/use-breakpoint.ts",
    "hooks/use-resize-observer.ts",
  ]),
]);

export default eslintConfig;
