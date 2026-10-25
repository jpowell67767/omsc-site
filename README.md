# Old Man Sports Club website

The OMSC website, published on Netlify. Every change saved here goes live automatically within a minute or two.

## What's in here

| Folder | What it is |
|---|---|
| `site/` | The finished website that Netlify publishes: the 8 pages, `images/` (all photos and videos) and `js/` (sliders, viewer). |
| `source/` | The page designs each page is built from (one file per page). Edit these, not `site/`. |
| `build/` | The small tool that turns `source/` into `site/`. |
| `netlify.toml` | Tells Netlify to publish the `site/` folder. |

## Pages

| Page | Built from |
|---|---|
| `index.html` (Home) | `source/Main.dc.html` |
| `pickleball.html` | `source/Pickleball.dc.html` |
| `cornhole.html` | `source/Cornhole.dc.html` |
| `pentathlon.html` | `source/Pentathlon.dc.html` |
| `champions-corner.html` | `source/ChampionsCorner.dc.html` |
| `event-statistics.html` | `source/EventStatistics.dc.html` |
| `leader-boards.html` | `source/LeaderBoards.dc.html` |
| `contact.html` | `source/Contact.dc.html` |

## Making a change

1. Edit the page in `source/`.
2. Rebuild: `python3 build/build.py source site` (needs Python 3 and Node 18 or newer).
3. Save (commit) both `source/` and `site/`. Netlify publishes the new version automatically.

## Daily event updates

- **Pickleball games** are kept between `// GPN-EVENTS-START` and `// GPN-EVENTS-END` in `source/Pickleball.dc.html` (taken from the OMSC page on Global Pickleball Network).
- **The next cornhole event** is kept between `// CORNHOLE-EVENT-START` and `// CORNHOLE-EVENT-END` in `source/Cornhole.dc.html` (taken from the cornhole sign-up form).

After either block changes, rebuild and commit as above.

## Contact form

The Contact page form uses Netlify Forms (form name `contact`). Submissions show up under **Forms** in Netlify, and email notifications are set there.
