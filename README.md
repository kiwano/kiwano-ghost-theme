# kiwano

A Ghost theme ported from the 2009 kiwano WordPress theme: black background, grey text, green headings and links, and a right-hand sidebar.

## Quick reference: cut

In the Ghost editor, type `/html` to add an HTML card where the cut should go, and paste:

```html
<hr id="cut">
```

See [Cut](#cut) below for details.

## Images

Images in posts are shown at most 400px wide and link to the full-size original. Wide, full-width and gallery images keep their sizes. An image you've linked yourself keeps your link.

## Fonts

- **ETL Fixed 16** (Latin-1 and Latin-2, from GNU intlfonts) loads first and is only 5 KB.
- **Unifont** covers every other character. It's split into chunks by Unicode range, so browsers only download the chunks a page uses.

Both are 16px bitmap fonts, so the CSS keeps sizes at 16px or 32px.

To rebuild the fonts, run `build_fonts.py` (it needs `fonttools` and `brotli`):

    python3 build_fonts.py lt1-16-etl.bdf lt2-16-etl.bdf unifont-18.0.01.otf assets/fonts > fonts.css

Then paste the printed `@font-face` rules over the ones at the top of `assets/css/screen.css`.

## Sidebar

- **Pages:** Ghost's primary navigation.
- **Tags:** all public tags.
- **Recent:** the 10 newest posts.
- **Links:** Ghost's secondary navigation, which replaces the old blogroll.
- **Meta:** links to the admin panel and the RSS feed.

## Licenses

- **Theme:** GPL-2.0-or-later.
- **ETL fonts:** freely usable (GNU intlfonts).
- **Unifont:** SIL OFL 1.1, or GPL-2.0-or-later with the font embedding exception.

## Cut

To show only the start of a post on the front page and tag pages, add an HTML card containing:

    <hr id="cut">

Everything after it is hidden behind a "Read more..." link, which jumps to that point in the full post. Posts without a cut are shown in full.
