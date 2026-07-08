# Texture credits

The 3D dashboard globe uses two equirectangular surface maps. Both are
resampled to 2048 x 1024 and re-compressed for size; they are used only for
visualisation, not for any physical computation.

- `earth_bluemarble.jpg` — Earth "Blue Marble" land/ocean map derived from
  NASA Visible Earth / Blue Marble imagery (NASA imagery is in the public
  domain). Source project: `webgl-earth` (`2_no_clouds` map).

- `moon.jpg` — Lunar surface albedo map, "2k Moon" texture by
  Solar System Scope (INOVE), licensed CC BY 4.0
  (https://www.solarsystemscope.com/textures/). Attribution retained here as
  required by the licence.

If these files are removed, the dashboard falls back to a smooth procedural
sphere so the app still runs on a clean install.
