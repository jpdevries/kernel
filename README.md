# Kernel

Pixel Bender filters from **Kernel**, a 2009 Adobe AIR app for previewing, animating and rendering Flash Player 10 shader effects, ported to WebGL2.

The original kernel sources (`.pbk`) are lost. Only the compiled bytecode (`.pbj`) survived, so each filter was decompiled with the disassembler in [`tools/`](tools/) and rewritten by hand as a GLSL ES 3.00 fragment shader. The ports reproduce the original math instruction for instruction.

## Filter bench

[`web/index.html`](web/index.html) is a single-file page that runs every kernel live on the GPU:

- one slider per kernel parameter, using the ranges stored in the bytecode
- ▶ on any parameter animates it back and forth, as Kernel's timeline did
- a compare wipe between the original and filtered image (a Fade control for SlashPix)
- Fit, 1:1 and 2× zoom, plus a grid, black or white backdrop for transparent pixels
- a generated 3200×2000 test image, or open, drop or paste your own
- the running GLSL shown next to the decompiled bytecode

Serve the folder over HTTP. Browsers refuse to load local image files into WebGL from `file://`.

```bash
python3 -m http.server 8000 --directory web
```

Then open <http://localhost:8000>.

## The kernels

| Kernel | Parameters | Effect |
|---|---|---|
| **HWave** | `sinX`, `freq`, `step` | Shifts each pixel sideways by `sinX · sin((x + step) / freq)` |
| **AcidTrip** | `sinX`, `freq`, `step` | The HWave displacement on the green channel only |
| **SlashPix** | `intensity`, `slashWidth`, `imageWidth` | Cuts the image into 45° slices and fades them out one after another |
| **CirclePix** | `circleDensity`, `radius` | Snaps pixels to a grid and drops pixels outside `radius` of a grid point to 50% alpha |
| **CirclePixSoft** | `circleDensity`, `radius` | CirclePix with a distance falloff on the red channel |
| **GeoTrio** | `squareMargin`, `radius`, `circleDensity` | Square, circle and diagonal-band masks that halve red, green and blue |

## How the port works

| Pixel Bender | WebGL2 |
|---|---|
| `outCoord()`: pixel centre, origin top-left | `vec2(gl_FragCoord.x, height - gl_FragCoord.y)` |
| `sampleNearest(src, p)`: pixel coords, transparent outside | `texelFetch` with a bounds check returning `vec4(0)` |
| `parameter float x` | `uniform float x` |
| `output pixel4 dst` | `fragColor`, clamped to 0–1 |

Each kernel is one `vec4 kernel(vec2 outCoord)` function. The page adds a shared prelude and draws one triangle that covers the canvas, which is sized to the image's real pixel dimensions. Images upload without a y-flip or alpha premultiplication, and the canvas uses `premultipliedAlpha: false`.

Where the bench departs from the bytecode:

- `step` is renamed `stepOffset` in GLSL, because `step()` is a built-in.
- SlashPix's top-left slice no longer divides 0 by 0, so it starts opaque.
- SlashPix's `slashWidth` is set as a percentage of the image width and converted to pixels for the shader. The original ran 0–100 px.

## Disassembler

[`tools/pbjdis.py`](tools/pbjdis.py) prints a `.pbj` file's metadata, parameters and instructions as readable pseudo-assembly. It needs only the Python 3 standard library.

```bash
python3 tools/pbjdis.py path/to/Filter.pbj
```

```
kernel HWave
  meta vendor = 'JP DeVries'
  in  float sinX  -> f0.z
      minValue: 0.0
      maxValue: 100.0
      defaultValue: 3.0
  ...
  f3.xyzw = sampleNearest(tex0, f0.xy)
  f3.x = rcp(f0.w)
  f3.x *= f2.w
  f2.w = sin(f3.x)
```

## Credits

The Orion Nebula test image (`web/orion.jpg`) was Kernel's original sample image and is a NASA Spitzer and Hubble composite (NASA/JPL-Caltech).

## License

[MIT](LICENSE)
