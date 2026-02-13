# Icons Directory

This directory should contain the extension icons in PNG format:

- `icon16.png` - 16x16 pixels (toolbar icon)
- `icon48.png` - 48x48 pixels (extension management page)
- `icon128.png` - 128x128 pixels (Chrome Web Store)

## Creating Icons

You can create these icons using:

1. **Online Tool**: Use https://favicon.io/ or https://realfavicongenerator.net/
2. **Design Software**: Figma, Sketch, or Photoshop
3. **SVG to PNG**: Convert the SVG below to multiple PNG sizes

## Suggested Design

A simple "digg" style logo with a play button overlay:
- Blue background (#4a9eff)
- White "d" letter with a small play triangle

## Temporary SVG Icon

Save this as `icon.svg` and convert to PNG at different sizes:

```svg
<svg width="128" height="128" viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg">
  <rect width="128" height="128" rx="24" fill="#4a9eff"/>
  <text x="20" y="95" font-family="Arial Black, sans-serif" font-size="80" font-weight="900" fill="white">d</text>
  <polygon points="75,50 75,80 100,65" fill="white"/>
</svg>
```

## Quick Generation Command

If you have ImageMagick installed:

```bash
# Create a simple blue square with text as placeholder
convert -size 128x128 xc:'#4a9eff' -gravity center -pointsize 64 -fill white -annotate 0 'd▶' icon128.png
convert icon128.png -resize 48x48 icon48.png
convert icon128.png -resize 16x16 icon16.png
```
