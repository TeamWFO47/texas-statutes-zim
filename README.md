# Texas Constitution & Statutes for Kiwix

All of Texas state law in one offline file you can search and read in [Kiwix](https://kiwix.org), with no internet needed.

## [⬇ Download texas-statutes_en_all_2026-03.zim (31 MB)](https://github.com/TeamWFO47/texas-statutes-zim/releases/download/v2026.03/texas-statutes_en_all_2026-03.zim)

From the [v2026.03 release](https://github.com/TeamWFO47/texas-statutes-zim/releases/tag/v2026.03). SHA256: `902f527fb7d4399fbd5826cd1314f7529dee68563e81acfe7e7d9c53c2f47fac`

## Install

You need Kiwix already running. Nothing else.

1. **Download the file** using the link above.
2. **Put it in your Kiwix zim folder.** On Project N.O.M.A.D. that folder is `/opt/project-nomad/storage/zim/`. You can drop the file there with FileBrowser, in its `zim` folder, or copy it in from a terminal. On Kiwix desktop or the Android app, just open the file.
3. **Rescan your library.** On Project N.O.M.A.D., open the Kiwix page and press **Rescan Library**. It shows up as **Texas Constitution & Statutes**.

## What's in it

- The Texas Constitution and all 30 Texas codes: Penal, Family, Transportation, Property, Government, Health and Safety, Education, Water, Tax, Occupations, Parks and Wildlife, and the rest.
- You can search all of it, by section number or by words.
- It works with no internet. When one law points to another, you can click straight through to it.
- Tables and fee schedules are included.

## Before you rely on it

- **It's a snapshot.** It is current through the 89th Legislature, 2nd Called Session, 2025 (and constitutional amendments approved in November 2025), as of **26 March 2026**. Later changes aren't in it.
- **It's not official.** This is an unofficial copy for reference. It isn't affiliated with the State of Texas or any government agency. For anything that matters legally, check [statutes.capitol.texas.gov](https://statutes.capitol.texas.gov/) or ask a lawyer.
- **It doesn't cover everything.** Agency rules (the Texas Administrative Code), court opinions, city and county ordinances, and federal law are not included.

Law text comes from the Texas Legislative Council. The data comes from [OpenStatutes.org](https://openstatutes.org/texconst/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## Build it yourself

You only need this section if you want to rebuild the ZIM, for example from a newer OpenStatutes release. There is no Texas law ZIM in the Kiwix catalog. These scripts build one from public data in about 5 minutes.

### How the pages are laid out

- **Pages:** one per chapter (one per article for the Constitution), 4,993 in all. There's also an index page for each code and a landing page linking all codes.
- **Section anchors:** every section has its own anchor, e.g. `PE/22.html#sec-22.011`. Section numbers and headings are kept exactly as Texas prints them ("Sec. 22.01. ASSAULT.").
- **Two versions of a section:** where Texas prints two versions of one section, each one is shown under TLC's own heading, e.g. "Text of section as amended by Acts 2021, 87th Leg., R.S., Ch. 849 (S.B. 705), Sec. 35".
- **Links:** every statute cross-reference is rewritten to point at the target's page and section anchor inside the archive.

### Build

You'll need Linux, `bash`, `curl`, Python 3.8 or later (standard library only), and Docker for the ZIM step.

```bash
git clone https://github.com/TeamWFO47/texas-statutes-zim.git
cd texas-statutes-zim
./build.sh
```

If your user isn't in the `docker` group, use `DOCKER="sudo docker" ./build.sh` instead.

`build.sh` runs five steps and stops if any of them fails:

1. **Download** the OpenStatutes.org release (31 JSON files, 31 HTML zips, about 258 MB) and TLC's official list of code names, then check every file against the release's `SHA256SUMS`. Downloads run one at a time with a 1-second pause, and files already verified are not downloaded again.
2. **Render** the HTML site (`scripts/render.py`).
3. **Verify** every page's text against TLC's own chapter page (`scripts/verify.py`).
4. **Link check** every internal link (`scripts/linkcheck.py`).
5. **Pack** the ZIM with `zimwriterfs` and run `zimcheck` on it (`scripts/make-zim.sh`, using `ghcr.io/openzim/zim-tools`).

The output goes to `$TXLAW_WORK/zim/texas-statutes_en_all_2026-03.zim`. All paths and settings are at the top of [`config.sh`](config.sh), and any of them can be overridden from the environment:

```bash
TXLAW_WORK=/data/txlaw ./build.sh     # put the ~1 GB of working files somewhere else
SKIP_ZIM=1 ./build.sh                 # stop after the verified HTML site, no Docker needed
```

To install the finished ZIM into a Kiwix library, run `./ship-zim.sh`. By default it copies into Project N.O.M.A.D.'s library folder; set `KIWIX_LIBRARY` to use a different one. Then rescan the library in Kiwix.

### Verified results (release 2026-03-26)

| Check | Result |
|---|---|
| Chapter pages whose text matches TLC's chapter page exactly | **4,993 of 4,993** |
| Statute cross-references resolved to an internal page and section | **125,825 of 125,883** (99.95%) |
| Dead internal links (140,866 links checked) | **0** |
| `zimcheck -A` | Pass |
| ZIM size | 31.2 MB (29.8 MiB), 5,044 entries, full-text index included |

**The 58 cross-references that don't resolve.** They are left as plain text, never as dead links:
- 21 have an empty target in TLC's own HTML.
- 26 point to Government Code §§531.0201x and 531.0204, which aren't in the release.
- 11 are Vernon's Civil Statutes references to bare numbers.

The release has 127,525 raw `GetStatute.aspx` mentions in total. 1,642 of them are in 7 stale files that the build excludes (see below). The remaining 125,883 are the real links.

### Where the data comes from

- **Law text:** the Texas Legislative Council, [Texas Constitution and Statutes](https://statutes.capitol.texas.gov/). Texas statutes are public law.
- **Data:** [OpenStatutes.org](https://openstatutes.org/texconst/), Texas Constitution and Statutes release 2026-03-26, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The release ships each code twice: as JSON, and as TLC's own chapter HTML (`<CODE>.htm.zip`). OpenStatutes is not affiliated with any government agency.
- **Official code names:** TLC's `statutes.capitol.texas.gov/assets/StatuteCodes.json`, used because some labels in the release are wrong, e.g. the Estates Code appears as "Subtitle Y. Texas Probate Code…".

The ZIM's landing page, every page footer, and the ZIM metadata all credit OpenStatutes.org (CC BY 4.0) and TLC.

### Why the build is "hybrid"

The plan was to render everything from the JSON. Checking it section by section against TLC's chapter HTML in the same release showed that **288 of 123,814 sections in the JSON are missing text**, and nothing in the JSON marks the gaps:

| Missing from the JSON | Sections |
|---|---|
| Table content (tax-rate tables, fee tables, forms) | 88 |
| Every line of a two-column list except the last, mostly fee schedules | 30 |
| First line(s) of multi-line subchapter headings | 170 |

**Example: Insurance Code §202.051, "General Fees Imposed on Insurers".** TLC lists 17 fees, starting with "(1) for filing an amendment to a certificate of authority if the charter is not amended … $100". The JSON contains **only item (17)**:

```
"Sec. 202.051.  GENERAL FEES IMPOSED ON INSURERS.  ... The amount of the fees may not exceed:\n(17)  for filing a statement under Subchapters D and E, Chapter 823, ..."
```

Live TLC agrees with the HTML, not the JSON. Labor Code §204.042 "Tax Rate Table" is another example: in the JSON it is the heading and "the employer's tax rate is:" with no table.

So, for each section, `render.py`:

1. Matches the JSON entry to its place in TLC's chapter HTML, using TLC's paired anchors (`<a name="22.01"></a><a name="62028.53357"></a>`).
2. Uses the **JSON text** when it matches TLC's text exactly, ignoring whitespace. That covers 123,526 sections.
3. Otherwise uses **TLC's own text** from the same release, with tables and line structure kept. That covers 288 sections. Run with `--mode json` to see what the JSON alone would give: 209 pages differ.
4. Rewrites every `GetStatute.aspx?Code=XX&Value=N` link to the target's page and section anchor through a section-to-page index. Those links point at a site that is now a single-page app, so they're broken online as well as offline.

It also cleans up these problems in the release:
- **Stale files:** 7 leftover copies (`pe.22_old.htm`, `cr.17 - Copy.htm`, `cr.17-old.htm`, `cr.62-old.htm`, `ed.51-old.htm`, `ed.51.htm.old-2018-10-12.htm`, `fa.58-old.htm`) were merged into the JSON. They're excluded, which drops 130 stale section versions, including a second, outdated copy of Penal Code Chapter 22.
- **Duplicates:** 867 exact duplicate JSON entries are removed.
- **Internal IDs:** the Constitution and Vernon's Civil Statutes carry internal IDs in place of section numbers. Their real numbers are recovered from TLC's anchors.
- **Missing sections:** 26 Estates Code sections that exist only in TLC's HTML are taken from there.

### Adapting it to other states

**What's known.** As of November 2026, OpenStatutes.org publishes only two collections, and both are Texas: the Constitution and Statutes, and the Texas Administrative Code. There is no data for other states, and they haven't published plans for more.

**What's unknown.** Whether OpenStatutes will add other states. If they do, whether those releases will include the source HTML alongside the JSON, which is what made the checks here possible. Also unknown is whether the Texas Administrative Code release (JSON, XML and USLM only, no HTML) has the same table problem. It hasn't been checked.

**What carries over to another state's data:**
- The overall approach: pair structured data with the official HTML, verify every section against it, and fall back to the official text where they differ.
- `linkcheck.py`, the page and landing structure, `make-zim.sh`, and `ship-zim.sh`.

**What is specific to Texas:**
- the anchor pairing and the stale-file filter in `render.py`
- the `GetStatute.aspx` link pattern and the code-name source

A new state needs its own way to read the source's sections and cross-references. If its source has no HTML to check against, compare the structured text against the official site on a sample of chapters before you trust it.

### Repository layout

```
build.sh               one-command build
config.sh              all settings (paths, snapshot, docker command, user agent)
ship-zim.sh            copy the finished ZIM into a Kiwix library
scripts/download.sh    fetch + SHA256-verify the OpenStatutes release and TLC code names
scripts/render.py      build the HTML site (hybrid JSON/TLC text, link rewriting)
scripts/verify.py      compare every page's text with TLC's chapter page
scripts/linkcheck.py   check every internal link and anchor
scripts/make-zim.sh    zimwriterfs + zimcheck in Docker
assets/                48x48 ZIM illustration
```

## License

The scripts are MIT licensed. See [LICENSE](LICENSE), which also covers the data:
- The Texas statute text is public law.
- The OpenStatutes.org data is CC BY 4.0, so any ZIM you build and share must credit OpenStatutes.org. The build does this automatically.
