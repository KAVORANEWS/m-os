#!/usr/bin/env bash
# Render M OS SVG branding sources into the raster assets used by packages.
# Rendered files are committed so CI/ISO builds do not depend on local fonts.
# Requirements: librsvg2-bin (rsvg-convert), imagemagick, fonts-inter, python3
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
B="$ROOT/branding"
R="$B/rendered"

for tool in rsvg-convert convert python3; do
    command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 1; }
done

python3 "$B/icons/generate_icons.py"
mkdir -p "$R"/{wallpaper,icons,boot,logos,calamares}

echo "Rendering wallpapers..."
for variant in dark light; do
    for res in 3840x2160 1920x1080; do
        w=${res%x*}; h=${res#*x}
        rsvg-convert -w "$w" -h "$h" "$B/wallpapers/mos-aurora-$variant.svg" -o "/tmp/mos-wp.png"
        convert /tmp/mos-wp.png -quality 90 -strip "$R/wallpaper/$variant-$res.jpg"
    done
    rsvg-convert -w 800 -h 450 "$B/wallpapers/mos-aurora-$variant.svg" -o /tmp/mos-wp.png
    convert /tmp/mos-wp.png -quality 85 -strip "$R/wallpaper/$variant-screenshot.jpg"
done
rm -f /tmp/mos-wp.png

echo "Rendering logos..."
for s in 16 22 24 32 48 64 128 256 512; do
    rsvg-convert -w "$s" -h "$s" "$B/logos/mos-logo.svg" -o "$R/logos/mos-logo-$s.png"
done
rsvg-convert -w 1200 -h 320 "$B/logos/mos-wordmark.svg" -o "$R/logos/mos-wordmark.png"

echo "Rendering application icons..."
for svg in "$B"/icons/scalable/*.svg; do
    n=$(basename "$svg" .svg)
    for s in 48 128 256; do
        mkdir -p "$R/icons/${s}x${s}"
        rsvg-convert -w "$s" -h "$s" "$svg" -o "$R/icons/${s}x${s}/$n.png"
    done
done

echo "Rendering boot splash..."
rsvg-convert -w 1024 -h 768 "$B/boot/grub-splash.svg" -o "$R/boot/grub-splash.png"

echo "Rendering installer branding..."
rsvg-convert -w 128 -h 128 "$B/logos/mos-logo.svg" -o "$R/calamares/logo.png"
rsvg-convert -w 1200 -h 320 "$B/logos/mos-wordmark.svg" -o /tmp/wm.png
convert -size 1000x560 xc:'#0B1020' \( /tmp/wm.png -resize 760x \) -gravity center -composite \
    "$R/calamares/welcome.png"
rsvg-convert -w 800 -h 440 "$B/wallpapers/mos-aurora-dark.svg" -o "$R/calamares/slide-bg.png"
rm -f /tmp/wm.png

echo "Rendering Plymouth assets..."
mkdir -p "$R/plymouth"
rsvg-convert -w 128 -h 128 "$B/logos/mos-logo.svg" -o "$R/plymouth/logo.png"
convert -size 12x12 xc:none -fill '#A5B4FC' -draw 'circle 6,6 6,1' "$R/plymouth/dot.png"

echo "Rendering global theme previews..."
mkdir -p "$R/previews"
for layout in modern classic; do
    rsvg-convert -w 1280 -h 720 "$B/wallpapers/mos-aurora-dark.svg" -o /tmp/pv.png
    if [ "$layout" = modern ]; then
        convert /tmp/pv.png -fill '#0B1020CC' -draw 'rectangle 0,0 1280,26' \
            -fill '#1C1F34E6' -draw 'roundrectangle 430,640 850,700 18,18' \
            -fill '#8B7CF8' -draw 'roundrectangle 452,650 492,690 10,10' \
            -fill '#38BDF8' -draw 'roundrectangle 504,650 544,690 10,10' \
            -fill '#10B981' -draw 'roundrectangle 556,650 596,690 10,10' \
            -fill '#F59E0B' -draw 'roundrectangle 608,650 648,690 10,10' \
            -fill '#EC4899' -draw 'roundrectangle 660,650 700,690 10,10' \
            -fill '#64748B' -draw 'roundrectangle 712,650 752,690 10,10' \
            -fill '#94A3B8' -draw 'roundrectangle 786,650 826,690 10,10' /tmp/pv2.png
    else
        convert /tmp/pv.png -fill '#0B1020E6' -draw 'rectangle 0,676 1280,720' \
            -fill '#8B7CF8' -draw 'roundrectangle 10,684 38,712 7,7' \
            -fill '#38BDF8' -draw 'roundrectangle 60,684 88,712 7,7' \
            -fill '#10B981' -draw 'roundrectangle 100,684 128,712 7,7' \
            -fill '#F59E0B' -draw 'roundrectangle 140,684 168,712 7,7' \
            -fill '#CBD5E1' -draw 'rectangle 1180,692 1260,700' /tmp/pv2.png
    fi
    convert /tmp/pv2.png -quality 88 "$R/previews/$layout-fullscreenpreview.jpg"
    convert /tmp/pv2.png -resize 400x225 "$R/previews/$layout-preview.png"
done
rm -f /tmp/pv.png /tmp/pv2.png

if command -v optipng >/dev/null; then
    find "$R" -name '*.png' -print0 | xargs -0 -n 8 optipng -quiet -o2
fi
echo "Done. Assets in $R"
du -sh "$R"
