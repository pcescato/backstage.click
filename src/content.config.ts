import { defineCollection } from "astro:content";
import { button, sectionsSchema } from "./sections.schema";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const contentLoader = (base: string) =>
  glob({ pattern: "**/[^_]*.{md,mdx}", base });

// Universal Page Schema
export const page = z.object({
  title: z.string(),
  description: z.string().optional(),
  image: z.string().optional(),
  draft: z.boolean().optional(),
  button: button.optional(),
  metaTitle: z.string().optional(),
  metaDescription: z.string().optional(),
  robots: z.string().optional(),
  excludeFromSitemap: z.boolean().optional(),
  excludeFromCollection: z.boolean().optional(),
  customSlug: z.string().optional(),
  canonical: z.string().optional(),
  keywords: z.array(z.string()).optional(),
  disableTagline: z.boolean().optional(),
  hasFooterDarkBackground: z.boolean().optional(),
  ...sectionsSchema,
});

// Marquee Schema
export const marqueeConfig = z.object({
  elementWidth: z.string(),
  elementWidthAuto: z.boolean(),
  elementWidthResponsive: z.string(),
  pauseOnHover: z.boolean(),
  reverse: z.enum(["reverse", ""]).optional(),
  duration: z.string(),
});

// Pages collection schema
const pagesCollection = defineCollection({
  loader: contentLoader("./src/content/pages"),
  schema: page,
});

// Prestations collection schema
const prestationsCollection = defineCollection({
  loader: contentLoader("./src/content/prestations"),
  schema: page.extend({
    icon: z.string().optional(),
    servicesSection: sectionsSchema.servicesSection.optional(),
  }),
});

// Export collections
export const collections = {
  prestations: prestationsCollection,
  pages: pagesCollection,
  sections: defineCollection({
    loader: contentLoader("./src/content/sections"),
  }),
  homepage: defineCollection({
    loader: contentLoader("./src/content/homepage"),
    schema: page,
  }),
};
