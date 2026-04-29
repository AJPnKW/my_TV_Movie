🎨 Network / Service Logo Spec

1. Canvas Size & Aspect
	Spec	Recommended	Reason
	Base size (logical)	96×48 px (2:1 aspect)	Fits most horizontal logos cleanly without distortion.
	Export size (actual PNG)	192×96 px	Gives retina/4K TV sharpness while still lightweight (<30 KB).
	Max displayed width	96 px (CSS scaled down if needed)	Keeps row alignment consistent.
	Safe zone / padding	4–6 px transparent margin all around	Prevents clipping in tight grids or highlight boxes.

	→ This ratio matches the “banner” feel of most network logos (wider than tall).

2. File Format & Background
	Setting	Value	Reason
	Format	.png	Maintains transparency + high color fidelity.
	Background	Transparent (not white/black)	Allows clean rendering on light/dark themes.
	Color model	sRGB	Ensures color consistency on TVs & browsers.
	Compression	Lossless (TinyPNG or ImageOptim acceptable)	Small file, crisp edges.

3. Color Style
	Variant	Usage
	Full-color logo	Default — provides recognition and appeal.
	Monochrome (white)	Used only in light-on-dark UI modes if full-color looks off.
	Monochrome (black)	Optional for white/light themes — but usually unnecessary if transparency works well.

	Rule of thumb: Prefer original brand colors unless they clash badly with the background (e.g., yellow-on-white).
	If conflict → auto-invert via CSS filter:

	img.network-logo.dark-theme { filter: brightness(0) invert(1); }

4. File Naming Convention
	<service_name>_logo.png
	Examples:
		netflix_logo.png
		ctv_logo.png
		cbc_logo.png
		disneyplus_logo.png
		prime_video_logo.png
	All lowercase, underscores, no spaces. This keeps file references consistent for automated matching.

	5. Storage & Reference
	Store at:
		/image/services_logos/
	Typical reference path in HTML or JSON:
	"logo": "image/services_logos/netflix_logo.png"

	Fallback (if missing):
	show the service name as text (e.g., “Netflix”) in the same slot.

6. Display Behavior in App
	Context	Target size	Style
	Episode / Movie row	64×32 px	Inline, aligned vertically center.
	Show popup header	80×40 px	Below TMDB/VidSrc row, max height 40 px.
	Config preview / Live TV grid	96×48 px	Uniform grid layout.

	CSS example:
	img.network-logo {
	  max-height: 40px;
	  max-width: 96px;
	  vertical-align: middle;
	  margin: 2px 4px;
	}

7. File Weight
	Keep each logo ≤ 40 KB (ideally under 25 KB).
	That way, 50–100 logos won’t delay load even on weaker Android sticks.

8. Visual Consistency Checklist

	✅ Centered horizontally and vertically
	✅ Transparent edges, no bounding boxes
	✅ No drop shadows baked into the PNG
	✅ No grayscale fuzz around letters
	✅ Use crisp edges for text logos (SVG → PNG export preferred)
	✅ No background gradients (flat preferred for clarity on TV)

9. Optional Pro Tier (Future)

	If you want ultra-clean scaling later, you can keep the SVG masters in:
	/image/services_logos_src/
	and generate .png versions via a small script (so resizing for 1×, 2×, 4× is automated).

🔧 TL;DR for Implementation
	Attribute	Value
	Canvas	192×96 px
	Aspect ratio	2:1
	Background	Transparent
	File format	PNG
	Color	Full color (transparent background)
	Naming	lowercase + _logo.png
	Size target	≤ 25 KB
	Folder	/image/services_logos/

If you’d like, I can create a Word or Markdown “Visual Asset Style Guide” with this spec table plus sample placement mockups (how logos render under Calendar, Shows, Movies, Live TV).
Would you like me to make that next?
