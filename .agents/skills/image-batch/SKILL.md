---
name: image-batch
description: >
  Execute a content batch file into finished images for @voronka.tm. Use when Operator
  hands you a file from funnel/batches/ and asks for the images. Covers generation,
  the 9:16 fit, QC, and where your job stops.
---

# Executing a content batch

Operator hands you `funnel/batches/NN-*.md`. **That file IS the plan — execute it directly, do not write an
implementation plan.** Read it plus `brand/character.md` and `brand/content-rules.md`. Nothing else is
required.

## The seven rules (already paid for — do not relearn them)

1. **The model draws your instructions.** No meta-words in a prompt — "safe zone", "label", "marker",
   pixel numbers, aspect ratios. They get printed into the image as gibberish. Only exact literal
   quoted strings and a short closed element list, ending with a ban on everything else.
2. **Never attach a text-bearing image as a reference.** The reference's text bleeds in as duplicated,
   corrupted ghost lines — this scrapped a whole run. Flat images generate **standalone**. The only
   sanctioned refs are the character sheets `ref-02-hero-closeup-flag-jacket.png` +
   `ref-03-full-sheet-poses-expressions.png`, always with *"do not copy any text, labels or logos from
   the reference images."*
3. **The wordmark is `@voronka.tm`, with the @.** Skip the corner stamp on character scenes whose neon
   sign already reads `voronka.tm`. Never a bare `voronka.tm` stamp.
4. **Mobile text sizes.** Headline like a phone's large title, body smaller. Never poster type.
5. **1:1 → 9:16 is a FIT, not a crop.** Run `python automations/ig-poster/crop916.py --folder X`. It
   scales the square to 1080 wide and extends the top/bottom edges to 1920 — nothing is cut, no image
   can fail on composition. `--crop --check` is legacy; don't use it unless the batch says to.
6. **Never name a container.** «column», «band», «strip», «panel» get *drawn* as a rectangle with hard
   edges that survive into the story. Say *"keep the left and right sides completely empty dark
   background."* Give the middle no noun. Dictate line breaks exactly as the batch table specifies.
   Props stack above, below, or in his hands — never "beside him".
7. **One wrong word → edit, anything worse → regenerate.** Edit recipe:
   `Fix the text to say "..." exactly, change nothing else.` A ghost line or a second bad letter means
   regenerate from scratch.

## QC before you show Operator anything

Run the full gate in `brand/content-rules.md` §9 and the character checklist in `brand/character.md`
§6. Zoom in on every Russian word — Cyrillic corrupts easily and one wrong letter kills the image.
Lime `#B4FF3A` is the only accent. No price anywhere, ever.

Compress before handing back or posting: The VPN is 2–4 Mb/s and raw 2K PNGs time out.
`Image.open(...).convert("RGB").save("x.jpg", "JPEG", quality=85, optimize=True)`.

## Where your job ends

- **Approved files. That's it.** Show Operator, wait for approval, hand the files over.
- Feed posts may be published with `automations/ig-poster/post.py` **only if Operator says so** — VPN must
  be on, and `--dry-run` first if anything in the pipeline changed.
- **Stories: never post them.** Operator posts stories himself from his phone so he can add the link sticker
  (`https://voronkatm.com`, «Бесплатный аудит») and assemble the highlight in-app the same day.
- Never touch anything that spends money.

## After the run

Update `STATE.md` with the batch status, log media IDs in `decisions/log.md`, and **write any new
generation failure into `brand/content-rules.md` immediately** — that's how this system compounds.
