import type { NavigationLink } from "@/types";
import type { TranslationFunction } from "@/lib/utils/i18nUtils";
import { filteredEnabled } from "@/lib/utils/filteredEnabled";

export type FooterMenuItem = {
  enable?: boolean;
  name: string;
  url: string;
  active?: boolean;
};

export type FooterMenuGroup = {
  label?: string;
  list: FooterMenuItem[];
};

const isFound = <T>(value: T | "Not Found"): value is T =>
  value !== "Not Found";

const getTranslationValue = <T>(
  t: TranslationFunction,
  key: string,
): T | undefined => {
  const value = t(key);

  return isFound<T>(value) ? value : undefined;
};

export const getHeaderMenu = (t: TranslationFunction): NavigationLink[] => {
  const menu =
    getTranslationValue<NavigationLink[]>(t, "menuConfig.header") ||
    getTranslationValue<NavigationLink[]>(t, "menuConfig.headerPrimary") ||
    getTranslationValue<NavigationLink[]>(t, "header") ||
    getTranslationValue<NavigationLink[]>(t, "headerPrimary") ||
    [];

  return Array.isArray(menu) ? filteredEnabled(menu) : [];
};

export const getFooterMenuGroups = (
  t: TranslationFunction,
): FooterMenuGroup[] => {
  const groupedFooter = getTranslationValue<FooterMenuGroup[]>(
    t,
    "menuConfig.footer",
  );

  if (Array.isArray(groupedFooter)) {
    return groupedFooter
      .map((group) => ({
        ...group,
        list: Array.isArray(group.list)
          ? group.list.filter((item) => item.enable !== false)
          : [],
      }))
      .filter((group) => group.list.length > 0);
  }

  // Older locale files keep footer columns as separate top-level arrays.
  return [
    {
      label: getTranslationValue<string>(t, "footer.quickLinksTitle"),
      list: getTranslationValue<FooterMenuItem[]>(t, "footerPrimary"),
    },
    {
      label: getTranslationValue<string>(t, "footer.servicesTitle"),
      list: getTranslationValue<FooterMenuItem[]>(t, "footerSecondary"),
    },
    {
      label: getTranslationValue<string>(t, "footer.informationTitle"),
      list: getTranslationValue<FooterMenuItem[]>(t, "footerTertiary"),
    },
  ]
    .map(({ label, list }) => ({
      label,
      list: Array.isArray(list)
        ? list.filter((item) => item.enable !== false)
        : [],
    }))
    .filter((group) => group.list.length > 0);
};
