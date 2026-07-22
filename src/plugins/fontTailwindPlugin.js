/**
 * Tailwind CSS Plugin to Register Custom Font Families
 *
 * This plugin reads font definitions from `./src/config/fonts.json`,
 * generates CSS variables for each font, and creates corresponding utility classes.
 *
 * Example:
 * If fonts.json contains:
 * [
 *   {
 *     "name": "Inter",
 *     "cssVariable": "--font-inter",
 *     "fallback": "sans-serif"
 *   }
 * ]
 *
 * It will generate:
 *   --font-inter: Inter, sans-serif;
 *   .font-inter {
 *     font-family: var(--font-inter);
 *   }
 */
import plugin from "tailwindcss/plugin";
import fontFamily from "../config/fonts.json";

const fontFamilies = Object.fromEntries(
  fontFamily.map((font) => [
    font.cssVariable?.replace("--font-", "") || font.name.toLowerCase(),
    `${font.name}, ${font.fallback || "sans-serif"}`,
  ]),
);

module.exports = plugin.withOptions(() => {
  return ({ addUtilities }) => {
    // Astro's font pipeline already defines each `--font-*` variable with a
    // metric-matched fallback stack (e.g. `Sora-<hash>, "… fallback: Arial", …`).
    // Re-declaring those variables here would shadow that optimized stack with a
    // plain `Name, sans-serif` value — which both renders the wrong font (the
    // unhashed family name is never loaded) and reintroduces font-swap layout
    // shift. So only emit the utilities and reference Astro's variable, keeping
    // the plain value purely as a fallback when the variable is absent.
    const fontUtilities = Object.fromEntries(
      Object.entries(fontFamilies).map(([k, v]) => [
        `.font-${k}`,
        { fontFamily: `var(--font-${k}, ${v})` },
      ]),
    );

    addUtilities(fontUtilities); // variants not necessary unless customized
  };
});
