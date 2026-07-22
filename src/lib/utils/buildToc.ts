import type { TocHeading } from "@/types";
import type { MarkdownHeading } from "astro";
import config from ".astro/config.generated.json";

interface TocOptions {
  startLevel: number;
  endLevel: number;
  ordered: boolean;
}

export default function buildToc(
  headings: MarkdownHeading[] | undefined,
): TocHeading[] {
  const { startLevel, endLevel, ordered } = config.settings.markup
    .tableOfContents as TocOptions;

  if (!headings) return [];

  const toc: TocHeading[] = [];
  const parentHeadings: TocHeading[] = [];

  headings.forEach((heading) => {
    if (heading.depth >= startLevel && heading.depth <= endLevel) {
      const newHeading: TocHeading = { ...heading, subheadings: [] };

      // Find the correct parent (or reset if depth is lower or equal)
      while (
        parentHeadings.length > 0 &&
        parentHeadings[parentHeadings.length - 1].depth >= newHeading.depth
      ) {
        parentHeadings.pop();
      }

      if (parentHeadings.length === 0) {
        toc.push(newHeading); // Top-level
      } else {
        const parent = parentHeadings[parentHeadings.length - 1];
        parent.subheadings.push(newHeading); // Nest under parent
      }

      parentHeadings.push(newHeading);
    }
  });

  if (ordered) sortToc(toc);

  return toc;
}

// Helper function to sort TOC entries alphabetically or based on other criteria
function sortToc(toc: TocHeading[]): void {
  toc.sort((a, b) => a.text.localeCompare(b.text));
  toc.forEach((heading) => {
    if (heading.subheadings.length > 0) {
      sortToc(heading.subheadings);
    }
  });
}
