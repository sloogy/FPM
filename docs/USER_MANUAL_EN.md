# FountainPen Manager – User Manual

**Version: v0.3.05 · Language: English**

This manual is the detailed guide to FountainPen Manager. The in-app wiki gives short, searchable explanations; this document covers workflows, safety logic, calculations, storage and troubleshooting in more depth.

---

## Contents

1. [Core philosophy](#1-core-philosophy)
2. [Starting, data directory and portable use](#2-starting-data-directory-and-portable-use)
3. [First steps](#3-first-steps)
4. [Interface, modes and navigation](#4-interface-modes-and-navigation)
5. [Dashboard](#5-dashboard)
6. [Pen management](#6-pen-management)
7. [Ink management](#7-ink-management)
8. [Nibs and paper](#8-nibs-and-paper)
9. [Rotation and suggestions](#9-rotation-and-suggestions)
10. [Rule engine](#10-rule-engine)
11. [Full Auto Mode](#11-full-auto-mode)
12. [Ink Safety Timer](#12-ink-safety-timer)
13. [Expenses and collection value](#13-expenses-and-collection-value)
14. [Wishlist](#14-wishlist)
15. [Statistics and writing samples](#15-statistics-and-writing-samples)
16. [Enthusiast Lab](#16-enthusiast-lab)
17. [Research and reference data](#17-research-and-reference-data)
18. [Settings](#18-settings)
19. [Languages](#19-languages)
20. [Updates](#20-updates)
21. [Backup and migration](#21-backup-and-migration)
22. [Troubleshooting and FAQ](#22-troubleshooting-and-faq)
23. [Reference](#23-reference)
24. [Glossary](#24-glossary)

---

## 1. Core philosophy

FountainPen Manager is not just an inventory database. It combines everyday use, care, rotation, spending and preservation of a collection.

Three principles guide the application:

1. **The engine recommends; the user decides.** Suggestions, warnings and scores never remove manual control.
2. **Safety has priority.** Combinations that may harm a pen are marked clearly and excluded from automatic selection unless the user deliberately overrides them.
3. **Optional depth.** Basic collection management works without maintaining every advanced field. Consumption, detailed rules and expert analyses can be enabled when useful.

---

## 2. Starting, data directory and portable use

### 2.1 Data location

The application stores the SQLite database, settings, media, local caches and backups in one data directory. The exact location depends on how the app is started:

1. `FPM_DATA_DIR` environment variable, when set.
2. Portable `data/` directory when using the supplied portable launcher.
3. Platform-specific user data directory for a normal installation.

The program files and the data directory are deliberately separated, so an update does not overwrite the collection.

### 2.2 Portable mode

Use `start-windows.cmd` on Windows or `start-linux.sh` on Linux. The launcher creates a local `data/` directory and configures Qt high-DPI handling. Keep the executable and `_internal/` directory together.

### 2.3 Offline use

Collection, rotation, rules, statistics and maintenance work offline. Only online research, image downloads and update checks need a connection.

---

## 3. First steps

Recommended sequence:

1. Add inks with colour family, properties and bottle size.
2. Add a nib separately or enter nib details directly while creating a pen.
3. Add pens with filling system and optional dimensions.
4. Fill a pen with an ink.
5. Open Rotation and generate suggestions.
6. Review Dashboard warnings and due maintenance.

On an empty database, the dashboard shows an onboarding panel and the Help page offers an interactive tour. Under **Settings → Reset**, the tour can be started immediately, forced for the next application start, or the four-step **setup assistant** can be opened again at any time. Existing collection data is not changed.

---

## 4. Interface, modes and navigation

### 4.1 Simple and Expert Mode

**Simple Mode** shows six core areas: Dashboard, Pens, Inks, Rotation, Help and Settings.

**Expert Mode** enables all 14 modules:

| # | Module | Purpose |
|---|---|---|
| 1 | Dashboard | Compact overview and alarm centre |
| 2 | Pens | Collection, values, dimensions and media |
| 3 | Inks | Bottles, properties and remaining amount |
| 4 | Nibs | Nib objects, grinds and compatibility |
| 5 | Paper | Paper and notebook profiles |
| 6 | Rotation | Current fills and suggestions |
| 7 | Expenses | Purchases, shipping, customs and value data |
| 8 | Wishlist | Planned purchases and conversion to collection items |
| 9 | Rules | Rule engine, timers and Full Auto |
| 10 | Help | Searchable in-app wiki and tour |
| 11 | Settings | Application configuration |
| 12 | Statistics | Collection and usage analysis |
| 13 | Writing Samples | Samples linked to pen, ink and paper |
| 14 | Enthusiast Lab | Collection gaps, care and enthusiast analysis |

The mode changes only navigation visibility. It does not delete or disable stored data.

### 4.2 Search and context help

The toolbar search is forwarded to the active module when that module provides a search field. `Ctrl+F` focuses it.

The **❔ Help for this tab** action opens the Help module and jumps directly to a relevant wiki chapter. The wiki itself is searchable across all help cards. Multiple words are matched together.

The **📖 Open manual** button opens the manual for the selected language:

- German: `docs/BENUTZERHANDBUCH_DE.md`
- English: `docs/USER_MANUAL_EN.md`
- French: `docs/MANUEL_UTILISATEUR_FR.md`

### 4.3 Laptop and window mode

Qt already works in logical pixels. FountainPen Manager therefore avoids multiplying all dimensions a second time by the operating-system DPI factor.

At startup, the main window is limited to the usable work area. On smaller laptops:

- Dashboard tiles wrap to fewer columns.
- Long pages use their own vertical scrolling.
- Minimum window size is capped by the available screen.
- Dialogs use scroll areas instead of hiding controls below the screen edge.

Use **Settings → Appearance → Auto** for most laptops and mixed-monitor setups. Use a larger manual preset only when the screen has enough working area.

### 4.4 Keyboard basics

- `Ctrl+N`: add an item on the active page when supported.
- `Ctrl+F`: focus search.
- `Ctrl+1 … Ctrl+9`: navigate to common pages.
- `Delete`: delete the selected table item only when the table has focus.
- Context menus expose frequent actions without adding permanent buttons everywhere.

---

## 5. Dashboard

The dashboard is a compact focus centre, not a complete inventory table.

### 5.1 Tiles

- **Collection & condition**: pen and ink counts, collection value, archive state and advisor notes.
- **Rotation & dwell time**: active fills, overdue fills and fills approaching their limit.
- **Service & locks**: problem pens, service cases and locked pens.
- **Recent activity**: recent fills and changes.
- **Savings goals**: appears only when BudgetManager goals are available.

### 5.2 Interaction

- Single-click a tile to focus and expand its detail table.
- Only one detail table remains open at a time.
- Click the same tile again to collapse it.
- Use the visible **“Open tab”** button to open the related module.
- Double-click a tile or table row remains available as a shortcut.
- `Enter` or `Space` expands; `Ctrl+Enter` opens the related module.

The Safety Timer table intentionally shows only overdue or soon-due fills. “Soon due” begins at **80%** of the allowed dwell time. The complete list is available under Rotation → Current fills.

---

## 6. Pen management

### 6.1 Pen dialog and safe data entry

The pen dialog is split into four pages:

1. Basic data
2. Nib
3. Details / value
4. Notes

Entries remain in the dialog while switching pages. Only **Save** writes the record to SQLite. **Cancel** or closing the window asks before discarding changed data.

Numeric fields accept regional decimal separators and visible units, for example:

- `143.5 mm`
- `24.8 g`
- `0.8 ml`
- `CHF 39.95`

The parser removes units and currency symbols safely. Switching to another page no longer resets a valid number to zero.

### 6.2 Main fields

Typical fields include brand, model, colour, filling system, purchase date, purchase price, market value, insurance value, dimensions, ink capacity, role, theme, tags and notes.

Supported filling systems include piston, vacuum, converter, cartridge and eyedropper.

### 6.3 Tags and status

Tags can mark a pen as Grail, problem pen, collector item, vintage or another collection-specific role. Tags influence suggestions, safety timing and analysis.

A pen may be available, in service, locked or archived. Service and locked pens remain visible in history but are not selected for new rotations.

### 6.4 Fixed pairing and must-include pen

- **Fixed pairing 💍** assigns one specific ink to a pen. Rotation, reroll and randomness respect it.
- **Must-include pen ⭐** receives a rotation slot before ordinary candidates, while its ink remains selectable.

### 6.5 Dimensions and comparison

The app stores closed, uncapped and posted length, maximum diameter, section diameter, weight and ink capacity.

The visual size comparison can overlay pens or show them in rows against a scale. Pens without the selected measurement are skipped rather than estimated.

### 6.6 Images and managed media

Images are copied into managed storage under the data directory. This prevents broken links when the original file is moved or renamed. Media files are limited and path-checked before import.

Back up the whole data directory, not just the SQLite file, to preserve images and writing samples.

---

## 7. Ink management

### 7.1 Ink properties

Store brand, name, colour family, bottle size, purchase data, wetness, flow, saturation, shading, sheen, shimmer, pigment, water resistance, feathering tendency and cleaning effort.

These properties feed the rule engine, Safety Timer and rotation score.

### 7.2 Remaining amount

Remaining amount tracking is optional. When enabled, filling a pen subtracts its stored capacity from the bottle. Stock never becomes negative. Empty or archived inks are excluded from suggestions but remain in history.

### 7.3 Duplicate active inks

By default, an ink already active in one pen is not suggested for another pen. This can be allowed in Settings. Fixed pairings remain an explicit exception.

---

## 8. Nibs and paper

### 8.1 Nibs

Nib objects can store manufacturer, physical size, writing width, material, grind, nibmeister, flexibility, stiffness, feedback and compatibility notes.

A specific pen–nib–feed installation can have its own setup notes. This avoids treating the same nib as identical in every pen body and feed.

### 8.2 Nib history

Nib changes can be documented per pen, including source, custom grind and setup experience.

### 8.3 Paper

Paper and notebooks store weight, surface, suitability for sheen and shading, feathering and bleed-through. A selected paper context influences rotation scoring.

---

## 9. Rotation and suggestions

### 9.1 Workflow

The engine generates a pen–ink combination for empty and available pens. You choose the number of active slots and may add paper or theme context.

Pens in service, locked pens, active pens and empty bottles are excluded automatically.

### 9.2 Score

The score combines:

- Rule bonuses and penalties
- Pen role and ink fit
- Nib and flow compatibility
- Paper suitability
- Colour diversity
- Time since last use
- Collection priorities
- Optional randomness

A score explanation shows why a combination ranked high or low.

### 9.3 Two-pass slot assignment

1. Must-include pens and fixed pairings are processed first.
2. Remaining slots are assigned to the best eligible candidates.

### 9.4 Reroll

Repeated suggestion runs avoid previously shown pen–ink pairs during the session. When a pen has exhausted its available pool, a new round starts for that pen. Fixed pairings are exempt.

### 9.5 Randomness

Randomness is configurable from 0% to 100%. Safety filters remain active at every value. Blocking hard rules and Full Auto rejects are never selected randomly, except for a deliberate fixed-pair override.

---

## 10. Rule engine

Rules may be hard or soft:

- **Soft rule**: changes score and displays advice.
- **Hard rule**: protects the pen and may block automatic use.

Warning levels:

- Info
- Warning
- Critical
- Blocked

Every rule may be disabled individually or through its rule group. Manual overrides are logged for traceability.

Example: vacuum filler + shimmer may be blocked because shimmer particles can settle in a system that is harder to clean.

---

## 11. Full Auto Mode

Full Auto is optional and must be enabled explicitly. It can:

- Reject risky combinations
- Prefer safer alternatives
- Skip locked or unavailable pens
- Apply score thresholds

It must never decide silently. Each action remains explainable through rule, reason, score, risk and chosen alternative.

---

## 12. Ink Safety Timer

The default base dwell time is reduced by risk factors. Typical factory limits include:

- Normal ink: **28 days**
- Shimmer ink: **14 days**
- Pigment / waterproof ink: shorter configured limit
- Grail pen: **21 days** maximum

The effective limit is the lowest applicable value. Example: a shimmer ink in a Grail pen uses `min(28, 14, 21) = 14 days` unless another rule shortens it further.

Dashboard status:

- Below 80%: normal, not shown in the warning table.
- From 80%: soon due.
- Above 100%: overdue.

All fills remain visible on the Rotation page.

---

## 13. Expenses and collection value

Expenses may include purchase price, shipping, customs, dealer, date and payment details. Pens can additionally store current market value and insurance value.

The app calculates collection totals and value changes using the selected regional format and currency settings. Foreign-currency values can use stored exchange rates.

---

## 14. Wishlist

Wishlist entries may represent pens, inks, nibs, paper, accessories or services. Store status, target price, notes and optional article media.

The purchase workflow converts a wishlist entry into the corresponding collection item and expense, reducing duplicate data entry.

---

## 15. Statistics and writing samples

Statistics cover brand distribution, filling systems, colour families, usage, expenses and value development.

Writing samples can link a pen, ink and paper. This enables side-by-side comparison and documents how a combination behaves over time.

---

## 16. Enthusiast Lab

The Enthusiast Lab provides optional deeper analysis, including:

- Colour-family gap analysis
- Collection health
- Cleaning effort by ink
- Bottle remaining amount and repurchase signals
- Nib-change history
- Collector and maintenance insights

These features remain optional and do not block ordinary collection management.

---

## 17. Research and reference data

### 17.1 Dimensions

Dimension lookup uses a conservative staged process and shows suggestions before applying them. Only empty fields are filled; manual values are never overwritten.

Confirmed results are cached locally for later use.

### 17.2 Sources

Suggestions identify their source:

- `manufacturer:<domain>`: official manufacturer source
- `online:<domain>`: open web source
- `cache`: previously confirmed local result

### 17.3 Manufacturer domains

Known manufacturers have built-in domains. Add or override brands through `manufacturer_domains.json` in the data directory. A value may be one domain string or a list of domains.

### 17.4 Images

Image search prefers official manufacturer results, then broader search. Imported images are copied into managed media storage.

---

## 18. Settings

| Page | Content |
|---|---|
| General | Language and general behaviour |
| Rotation & suggestions | Randomness, duplicate active inks and rotation behaviour |
| Appearance | Responsive UI scale and Simple / Expert Mode |
| Currency & region | Currency, number format, date format and exchange rates |
| Database & backup | Data location and backup actions |
| Import / export | Data transfer and available exports |
| Reset / danger zone | Protected reset operations |
| Updates | Manual update check |
| About | Version and build information |

Changes to scale should remain within the available screen area. Auto is the recommended default.

---

## 19. Languages

Visible UI text is stored outside the Python code in JSON files for German, English and French. Translation key parity is checked automatically.

Technical terms such as Sheen, Shimmer and Reroll may remain unchanged when that is clearer for fountain-pen users.

The in-app wiki and full manual are available in all three languages in v0.2.97.

---

## 20. Updates

The app checks for updates only when requested from Settings. It reads the official release manifest and does not run a hidden background connection.

Portable users replace the program directory while keeping the data directory. Create a backup first.

---

## 21. Backup and migration

A complete backup includes:

- SQLite database
- Settings
- Images and writing samples
- Local research cache
- User domain overlay
- Backup history as desired

The safest method is to close the app and copy the entire data directory.

To move to another computer, copy the data directory and point `FPM_DATA_DIR` to it or place it in the platform default location.

---

## 22. Troubleshooting and FAQ

**I only see part of the page on my laptop.**
Use Settings → Appearance → Auto, maximise the window for a test and use the page’s own scroll area. Dashboard detail tables are intentionally opened one at a time.

**Dimensions or prices disappear when I change pages in the pen dialog.**
This was corrected in v0.2.95. Units such as `mm`, `g`, `ml` and currency symbols are parsed safely. v0.2.97 also warns before discarding an edited dialog.

**The dashboard does not list all active fills.**
The warning table shows only fills at or above 80% of their safety limit. Open Rotation → Current fills for the complete list.

**The same ink is suggested repeatedly.**
Check for a fixed pairing. Otherwise rerun suggestions; reroll avoids pairs already shown in the current session.

**A pen never appears in suggestions.**
Check whether it is already filled, in service, locked, rotation-locked or archived.

**How do I find help for the current page?**
Use ❔ Help for this tab. Then refine the result with the wiki search or `Ctrl+F`.

**Online research returns no results.**
The feature needs internet access. Check brand spelling and optional manufacturer-domain overrides. Offline collection functions continue to work.

**A warning is too strict.**
Disable the individual rule or its group, lower a custom rule level, or use a documented one-time override.

---

## 23. Reference

Important configurable concepts include:

| Concept | Typical default |
|---|---:|
| Normal cleaning interval | 28 days |
| Shimmer cleaning interval | 14 days |
| Grail maximum interval | 21 days |
| Dashboard soon-due threshold | 80% |
| Default currency | CHF |
| Default Simple Mode modules | 6 |
| Expert Mode modules | 14 |

Exact values in the Rules and Settings pages take precedence over this manual when the user changes them.

---

## 24. Glossary

**EDC** – Every Day Carry; the small set of pens used daily.

**Feathering** – Ink spreading along paper fibres.

**Fixed pairing** – A deliberate pen–ink assignment that rotation always respects.

**Grail pen** – A particularly valuable or emotionally important pen.

**Hard rule** – A safety rule that may block automatic selection.

**Ink Safety Timer** – Tracks how long an ink remains in a pen.

**Override** – Deliberately accepting and recording a warning or block.

**Reroll** – Generating another set of suggestions while avoiding previously shown pairs.

**Sheen** – Metallic-looking surface colour visible on suitable paper.

**Shimmer** – Suspended glitter particles requiring extra cleaning care.

**Soft rule** – A recommendation that changes score without blocking use.

**Vac / vacuum filler** – A high-capacity filling system that is typically more involved to clean.
