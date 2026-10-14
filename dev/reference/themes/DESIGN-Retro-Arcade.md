---
version: "alpha"
name: "Retro Arcade Pixelado"
description: "Nostalgic and playful retro landing page for an online classic arcade. Ideal for landing pages, modern websites. AI-ready template."
colors:
  primary: "#0000FF"
  secondary: "#FF0000"
  tertiary: "#FFFF00"
  neutral: "#000000"
  surface: "#00FF00"
  accent: "#800080"
typography:
  h1:
    fontFamily: Press Start 2P
    fontSize: 2.5rem
    fontWeight: 700
  body-md:
    fontFamily: Press Start 2P
    fontSize: 1rem
    fontWeight: 400
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral}"
    padding: 12px
---

## Overview

Nostalgic and playful retro landing page for an online classic arcade. Ideal for landing pages, modern websites. AI-ready template. The pixel wasn't a choice. It was a constraint. When Namco shipped Pac-Man in 1980, those chunky 8×8 tile grids weren't aesthetic decisions — they were the literal ceiling of what hardware could render. Designers worked within brutal limitations: 16 colors, fixed palettes, sprites measured in single-digit pixels. And yet, within those constraints, they built an entire visual language. The glow of a CRT scan line. The flicker of a ghost turning blue. Every pixel earned its place.

What's remarkable is how that language refused to die. When indie developers in the late 2000s reached for pixel art, they weren't just being nostalgic — they were choosing clarity. A pixel-art character reads instantly at any scale. The grid enforces intentionality: you can't hide behind anti-aliasing or gradients. Every single dot is a decision.

Today the aesthetic lives in places its creators never imagined. Arcade bars in Brooklyn. Crypto projects chasing 8-bit credibility. Streetwear brands printing sprite sheets on hoodies. The constraint became the style. The limitation became the look.

- Density: 5/10 — Balanced
- Variance: 7/10 — Dynamic
- Motion: 4/10 — Subtle

- **Style:** Nostalgic, Playful, Pixelated
- **Keywords:** retro gaming, arcade, pixel art, nostalgic, playful, classic, 8-bit, vibrant, fun, community
- **Era:** 1980s Arcade
- **Light/Dark:** ✗ No / ✓ Full

## Colors

- **Azul Elétrico** (#0000FF) — Accent highlight, links and focus states
- **Vermelho Cereja** (#FF0000) — Error states, destructive actions
- **Amarelo Brilhante** (#FFFF00) — Warning states, attention indicators
- **Preto** (#000000) — Dark surface, primary background
- **Verde Limão** (#00FF00) — Success states, positive indicators
- **Roxo** (#800080) — Accent color, emphasis elements
- **Ciano** (#00FFFF) — Extended palette, decorative use
- **Branco** (#FFFFFF) — Secondary surface


## Typography

- **Display / Hero:** Press Start 2P — Weight 700, tight tracking, used for headline impact
- **Body:** Press Start 2P — Weight 400, 16px/1.6 line-height, max 72ch per line
- **UI Labels / Captions:** Press Start 2P — 0.875rem, weight 500, slight letter-spacing
- **Monospace:** JetBrains Mono — Used for code, metadata, and technical values

Scale:
- Hero: clamp(2.5rem, 5vw, 4rem)
- H1: 2.25rem
- H2: 1.5rem
- Body: 1rem / 1.6
- Small: 0.875rem


## Layout

- **Grid:** CSS Grid primary. Max-width containment: 1280px centered with 1.5rem side padding.
- **Spacing rhythm:** Balanced. Base unit: 0.5rem (8px).
- **Section vertical gaps:** clamp(4rem, 8vw, 8rem).
- **Hero layout:** Asymmetric composition.
- **Feature sections:** Asymmetric grid with varied card sizes. No 3-equal-columns.
- **Mobile collapse:** All multi-column layouts collapse below 768px. No horizontal overflow.
- **z-index contract:** base (0) / sticky-nav (100) / overlay (200) / modal (300) / toast (500).


## Elevation & Depth

Pixel art em elementos gráficos, tipografia de 8-bit, texturas de tela CRT, bordas com efeito de scanline, micro-interações de clique com som de "blip", animações de transição de tela com efeito de "glitch" ou "fade" rápido.

- **Physics:** Ease-out curves, 200-300ms duration. Smooth and predictable.
- **Entry animations:** Fade + translate-Y (16px → 0) over 420ms ease-out. Staggered cascades for lists: 80ms between items.
- **Hover states:** Subtle color shift + shadow adjustment over 200ms.
- **Page transitions:** Fade only (200ms).
- **Performance:** Only transform and opacity animated. No layout-triggering properties.


## Shapes

Base corner radius: 8px. See rounded tokens in front matter for the full scale.


## Components

- **Primary Button:** Subtly rounded (0.5rem) shape. Accent color fill. Hover: 8% darken + subtle lift shadow. Active: -1px translate tactile press. Font weight 600. No outer glows.
- **Secondary / Ghost Button:** Outline variant. 1.5px border in muted color. Text in primary color. Hover: subtle background fill.
- **Cards:** Subtly rounded (0.5rem) corners. Surface background. Subtle shadow (0 2px 12px rgba(0,0,0,0.06)). 1px border stroke.
- **Inputs:** Label above input. 1px border stroke. Focus ring: 2px accent color offset 2px. Error text below in semantic red. No floating labels.
- **Navigation:** Primary surface background. Active item: accent color indicator. Font weight 500 when active.
- **Skeletons:** Shimmer animation matching component dimensions. No circular spinners.
- **Empty States:** Icon-based composition with descriptive text and action button.


## Do's and Don'ts

- No emojis in UI — use icon system only (Lucide, Heroicons)
- No pure black (#000000) — use off-black or charcoal variants
- No oversaturated accent colors (saturation cap: 80%)
- No 3-column equal-width feature layouts — use zig-zag or asymmetric grid
- No `h-screen` — use `min-h-[100dvh]`
- No AI copywriting clichés: "Elevate", "Seamless", "Unleash", "Next-Gen"
- No broken external image links — use picsum.photos or inline SVG
- No generic lorem ipsum in demos

- Do Pixel art
- Do Tipografia de 8-bit
- Do Texturas de tela CRT
- Do Bordas com scanline
- Do Micro-interações com som
- Do Animações de transição de tela.


background
background: #000000, color: #FFFF00, text-shadow: 2px 2px #FF0000, border: 2px solid #00FFFF, font-family: "Press Start 2P, cursive", animation: crt-scanline 5s linear infinite, .pixel-art-graphic, .8bit-font, .scanline-effect.

variables
--electric-blue: #0000FF, --cherry-red: #FF0000, --bright-yellow: #FFFF00, --black-bg: #000000, --font-pixel: "Press Start 2P, cursive", --crt-scanline-effect: url("scanline.png"), --border-neon: 2px solid #00FFFF.




## Use Case

Landing pages, Modern websites

<!-- Source: https://designmd.app/library/retro-arcade-pixelado · designmd.app -->

