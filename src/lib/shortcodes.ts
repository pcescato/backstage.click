// Shortcodes made available to MDX content via the `components` prop on
// `<Content />`. Replaces the auto-injected imports from `astro-auto-import`.
// Pass this map wherever MDX collections are rendered: `<Content components={shortcodes} />`.
import Button from "@/components/Button.astro";
import ListCheck from "@/shortcodes/ListCheck.astro";
import Accordion from "@/shortcodes/Accordion.astro";
import Notice from "@/shortcodes/Notice.astro";
import Tabs from "@/shortcodes/Tabs.astro";
import Tab from "@/shortcodes/Tab.astro";
import Testimonial from "@/shortcodes/Testimonial.astro";
import ImageList from "@/shortcodes/ImageList.astro";
import ImageItem from "@/shortcodes/ImageItem.astro";
import Card from "@/shortcodes/Card.astro";
import CardWrapper from "@/shortcodes/CardWrapper.astro";
import VideoInline from "@/shortcodes/VideoInline.astro";

export const shortcodes = {
  Button,
  ListCheck,
  Accordion,
  Notice,
  Tabs,
  Tab,
  Testimonial,
  ImageList,
  ImageItem,
  Card,
  CardWrapper,
  VideoInline,
};
