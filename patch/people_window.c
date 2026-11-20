/* "People" window for Astra Novum (0.1.23): injected into astra_client.exe as its own section.
   Hooked in place of the call to the province panel: draws the panel as before, then, when the map is
   "Peoples of 2240" and a province is selected, a separate window on the right with the peoples of that
   province as tabs and the chosen people's record and written history.
   Built by tools/build_people_window.py (clang, MS x64 ABI, no CRT, position independent). */
#include <stdint.h>
#include "people_data.h"

typedef struct { uint64_t len; const char *p; } SV;
typedef struct { float x, y, w, h; } Rect;

typedef void  (*ProvPanelFn)(void *ui, void *view, char *L, void *r9);
typedef Rect *(*PanelFn)(Rect *out, void *ui, Rect *r, SV *title);
typedef char  (*ButtonFn)(void *ui, Rect *r, SV *label, uint64_t flags);
typedef float (*TextFn)(void *ui, float x, float y, SV *s, float *color);
typedef void  (*FillFn)(void *ui, Rect *r, float *color);

#define RVA_PROV_PANEL 0x175c60u
#define RVA_PANEL      0x1662a0u
#define RVA_BUTTON     0x166760u
#define RVA_TEXT       0x165300u
#define RVA_FILL       0x1633e0u

static char *image_base(void)
{
    char *peb;
    __asm__ volatile("movq %%gs:0x60, %0" : "=r"(peb));
    return *(char **)(peb + 0x10);
}

/* state kept between frames */
/* mode 0: the selected province's peoples; 1: the A to Z list of all peoples; 2: one people from the list */
static struct { uint32_t prov; uint32_t tab; uint32_t closed; uint32_t page; uint32_t mode; uint32_t person; uint32_t lpage; uint32_t pad; }
    st = { 0xFFFFFFFFu, 0, 0, 0, 0, 0, 0, 0 };

static uint32_t slen(const char *s) { uint32_t n = 0; while (s[n]) n++; return n; }
/* length of b if the title a starts with the whole name b (followed by its end or a non-letter), else 0 */
static uint32_t prefix(const char *a, uint64_t n, const char *b)
{
    uint32_t i = 0;
    for (; b[i]; i++) if (i >= n || a[i] != b[i]) return 0;
    if (i < n) { char c = a[i]; if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) return 0; }
    return i;
}
static const char *str(uint32_t off) { return PW_STR + off; }

/* a people's map colour as an on-screen (sRGB) colour */
static void colour_of(uint32_t rgb, float a, float *c)
{
    c[0] = (float)((rgb >> 16) & 255u) / 255.0f; c[1] = (float)((rgb >> 8) & 255u) / 255.0f;
    c[2] = (float)(rgb & 255u) / 255.0f; c[3] = a;
}

static float text(TextFn t, void *ui, float x, float y, const char *s, uint32_t n, float *col)
{
    SV v = { n, s };
    return t(ui, x, y, &v, col);
}

/* word-wrapped text; returns the y below it. Lines before `skip` are not drawn (paging); if the text does
   not fit above ymax, *more is set and drawing stops. */
static float wrapx(TextFn t, void *ui, float x, float y, float w, const char *s, float *col, float lh, float ymax,
                   float cw, uint32_t skip, int *more)
{
    uint32_t per = (uint32_t)(w / cw);
    if (per < 8) per = 8;
    uint32_t n = slen(s), i = 0, line = 0;
    while (i < n) {
        if (s[i] == ' ') { i++; continue; }
        uint32_t end = i + per, cut;
        if (end >= n) cut = n;
        else {
            cut = end;
            while (cut > i && s[cut] != ' ') cut--;
            if (cut == i) cut = end;
        }
        uint32_t nl = i;
        while (nl < cut && s[nl] != '\n') nl++;
        if (line >= skip) {
            if (y + lh > ymax) { if (more) *more = 1; return y; }
            text(t, ui, x, y, s + i, nl - i, col);
            y += lh;
        }
        line++;
        i = (nl < cut) ? nl + 1 : cut;
    }
    return y;
}

static float wrap(TextFn t, void *ui, float x, float y, float w, const char *s, float *col, float lh, float ymax, float cw)
{
    int more = 0;
    return wrapx(t, ui, x, y, w, s, col, lh, ymax, cw, 0, &more);
}

static void row(TextFn t, void *ui, float x, float *y, float w, const char *label, const char *val,
                float *cl, float *cv, float lh, float ymax, float cw)
{
    if (!val[0]) return;
    text(t, ui, x, *y, label, slen(label), cl);
    *y = wrap(t, ui, x + cw * 11.0f, *y, w - cw * 11.0f, val, cv, lh, ymax, cw);
}


static const char *lit(const char *p) { __asm__("" : "+r"(p)); return p; }   /* no absolute pointers in data */

static int btn(ButtonFn button, void *ui, float x, float y, float w, float h, const char *label)
{
    Rect b = { x, y, w, h };
    SV s = { slen(label), label };
    return button(ui, &b, &s, 0) != 0;
}

/* one people's record: facts and the paged written history, from y down to ymax */
static void record(TextFn t, ButtonFn button, void *ui, const PwPeople *G, float x, float y, float w, float ymax,
                   float lh, float cw, float *col_text, float *col_dim)
{
    row(t, ui, x, &y, w, "Family", str(G->family), col_dim, col_text, lh, ymax, cw);
    row(t, ui, x, &y, w, "Language", str(G->language), col_dim, col_text, lh, ymax, cw);
    row(t, ui, x, &y, w, "Faith", str(G->faith), col_dim, col_text, lh, ymax, cw);
    row(t, ui, x, &y, w, "Number", str(G->number), col_dim, col_text, lh, ymax, cw);
    row(t, ui, x, &y, w, "From", str(G->parents), col_dim, col_text, lh, ymax, cw);
    row(t, ui, x, &y, w, "Heartland", str(G->strongholds), col_dim, col_text, lh, ymax, cw);
    y += lh * 0.5f;
    float bh = lh + 4.0f, ytext = ymax - bh - 6.0f;
    uint32_t per_page = (uint32_t)((ytext - y) / lh); if (per_page < 3) per_page = 3;
    int more = 0;
    wrapx(t, ui, x, y, w, str(G->description), col_text, lh, ytext, cw, st.page * per_page, &more);
    if (more || st.page > 0) {
        char lab[24]; uint32_t n = 0; uint32_t pg = st.page + 1;
        const char *pl = lit("Page "); for (uint32_t i = 0; pl[i]; i++) lab[n++] = pl[i];
        if (pg >= 10) lab[n++] = (char)('0' + pg / 10 % 10);
        lab[n++] = (char)('0' + pg % 10);
        text(t, ui, x + w * 0.5f - cw * 3.5f, ytext + 8.0f, lab, n, col_dim);
        float bw = cw * 9.0f;
        if (st.page > 0 && btn(button, ui, x, ytext + 4.0f, bw, bh, lit("< Prev"))) st.page--;
        if (more && btn(button, ui, x + w - bw, ytext + 4.0f, bw, bh, lit("Next >"))) st.page++;
    }
}

__attribute__((used)) void pw_hook(void *ui, void *view, char *L, void *r9)
{
    char *B = image_base();
    ((ProvPanelFn)(B + RVA_PROV_PANEL))(ui, view, L, r9);

    if (*(int32_t *)(L + 0xc0) != 1) return;                 /* only on the "Peoples of 2240" map */
    if (!*(uint8_t *)(L + 0x160)) return;                    /* province panel shown */
    if (*(uint64_t *)(L + 0x190) == 0) return;               /* a province (not just a planet) selected */
    const char *pname = *(const char **)(L + 0x168);
    uint64_t plen = *(uint64_t *)(L + 0x170);
    if (!pname || plen == 0 || plen > 200) return;

    uint32_t prov = 0xFFFFFFFFu;
    uint32_t bestLen = 0;
    for (uint32_t i = 0; i < PW_NPROV; i++) {
        uint32_t m = prefix(pname, plen, str(PW_PROV[i].name));
        if (m > bestLen) { bestLen = m; prov = i; }
    }
    if (prov == 0xFFFFFFFFu) {                               /* fallback: the name anywhere in the title */
        for (uint32_t i = 0; i < PW_NPROV; i++) {
            const char *nm = str(PW_PROV[i].name);
            uint32_t ln = slen(nm);
            if (ln <= bestLen || ln > plen) continue;
            for (uint64_t o = 1; o + ln <= plen; o++)
                if (prefix(pname + o, plen - o, nm)) { bestLen = ln; prov = i; break; }
        }
    }
    if (prov == 0xFFFFFFFFu) return;
    if (prov != st.prov) { st.prov = prov; st.tab = 0; st.closed = 0; st.page = 0; st.mode = 0; }
    if (st.closed) return;

    PanelFn panel = (PanelFn)(B + RVA_PANEL);
    ButtonFn button = (ButtonFn)(B + RVA_BUTTON);
    TextFn t = (TextFn)(B + RVA_TEXT);
    FillFn fill = (FillFn)(B + RVA_FILL);
    float *col_text = (float *)((char *)ui + 0x84);
    float *col_dim = (float *)((char *)ui + 0x74);
    float cw = *(float *)ui, ch = *(float *)((char *)ui + 4);
    if (cw < 4.0f || cw > 40.0f) cw = 8.0f;
    if (ch < 8.0f || ch > 60.0f) ch = 14.0f;
    float lh = ch + 4.0f;

    float W = *(float *)L, H = *(float *)(L + 4);
    float pw = cw * 56.0f; if (pw > W * 0.42f) pw = W * 0.42f; if (pw < 300.0f) pw = 300.0f;
    float rightPad = *(uint8_t *)(L + 0x159) ? 346.0f : 26.0f;
    float px = W - rightPad - pw, py = 94.0f;
    float ph = H - py - 150.0f; if (ph > 720.0f) ph = 720.0f; if (ph < 200.0f) ph = 200.0f;

    const PwProv *P = &PW_PROV[prov];
    uint32_t ntab = 0;
    for (uint32_t k = 0; k < 3; k++) if (P->who[k] != 0xFFFF) ntab = k + 1;
    if (ntab == 0 && st.mode == 0) st.mode = 1;
    if (st.tab >= ntab) st.tab = 0;

    const PwPeople *G = st.mode == 1 ? 0 : &PW_PEOPLE[st.mode == 2 ? st.person : P->who[st.tab]];
    Rect r = { px, py, pw, ph }, c;
    const char *ttl = G ? str(G->name) : lit("Peoples of 2240, A to Z");
    SV title = { slen(ttl), ttl };
    panel(&c, ui, &r, &title);
    if (btn(button, ui, px + pw - 22.0f, py + 3.0f, 18.0f, 18.0f, lit("x"))) { st.closed = 1; return; }
    if (st.mode != 1 && btn(button, ui, px + pw - 22.0f - 8.0f - cw * 6.0f, py + 3.0f, cw * 6.0f, 18.0f, lit("A-Z")))
        { st.mode = 1; st.page = 0; return; }
    float accent[4];
    colour_of(G ? G->colour : 0x8aa0b8u, 1.0f, accent);
    Rect bar = { c.x, c.y - 3.0f, c.w, 3.0f };                /* accent line in the people's colour */
    fill(ui, &bar, accent);

    float x = c.x + 4.0f, y = c.y + 2.0f, w = c.w - 8.0f, ymax = c.y + c.h - 4.0f;
    float bh = lh + 4.0f;

    if (st.mode == 1) {
        /* every people, A to Z, two columns, a page at a time; click one to read about it */
        float colw = (w - 8.0f) * 0.5f;
        uint32_t rows = (uint32_t)((ymax - y - bh - 10.0f) / (bh + 3.0f)); if (rows < 2) rows = 2;
        uint32_t per = rows * 2, pages = (PW_NPEOPLE + per - 1) / per;
        if (st.lpage >= pages) st.lpage = pages - 1;
        for (uint32_t k = 0; k < per; k++) {
            uint32_t i = st.lpage * per + k;
            if (i >= PW_NPEOPLE) break;
            const PwPeople *Q = &PW_PEOPLE[PW_ORDER[i]];
            float bx = x + (k >= rows ? colw + 8.0f : 0.0f), by = y + (float)(k % rows) * (bh + 3.0f);
            char lab[64]; uint32_t n = 0;
            lab[n++] = ' '; lab[n++] = ' ';
            const char *nm = str(Q->shortname);
            uint32_t maxc = (uint32_t)(colw / cw) - 1; if (maxc > 60) maxc = 60;
            for (uint32_t j = 0; nm[j] && n < maxc; j++) lab[n++] = nm[j];
            Rect b = { bx, by, colw, bh };
            SV sv = { n, lab };
            if (button(ui, &b, &sv, 0)) { st.mode = 2; st.person = PW_ORDER[i]; st.page = 0; }
            float sw[4]; colour_of(Q->colour, 1.0f, sw);
            Rect sq = { bx + 5.0f, by + (bh - 10.0f) * 0.5f, 10.0f, 10.0f };
            fill(ui, &sq, sw);
        }
        float yb = ymax - bh;
        float bw = cw * 9.0f;
        if (st.lpage > 0 && btn(button, ui, x, yb, bw, bh, lit("< Prev"))) st.lpage--;
        if (st.lpage + 1 < pages && btn(button, ui, x + w - bw, yb, bw, bh, lit("Next >"))) st.lpage++;
        if (ntab > 0 && btn(button, ui, x + w * 0.5f - cw * 7.0f, yb, cw * 14.0f, bh, lit("This province"))) { st.mode = 0; st.page = 0; }
        return;
    }

    if (st.mode == 2) {
        if (btn(button, ui, x, y, cw * 16.0f, bh, lit("< All peoples"))) { st.mode = 1; return; }
        if (ntab > 0 && btn(button, ui, x + w - cw * 14.0f, y, cw * 14.0f, bh, lit("This province"))) { st.mode = 0; st.page = 0; return; }
        y += bh + 10.0f;
        record(t, button, ui, G, x, y, w, ymax, lh, cw, col_text, col_dim);
        return;
    }

    text(t, ui, x, y, lit("Peoples of "), 11, col_dim);
    text(t, ui, x + cw * 11.0f, y, pname, (uint32_t)plen, col_text);
    y += lh + 2.0f;

    /* one tab per people of the province */
    float tw = (w - 8.0f * (float)(ntab - 1)) / (float)ntab;
    for (uint32_t k = 0; k < ntab; k++) {
        const PwPeople *Q = &PW_PEOPLE[P->who[k]];
        char lab[64]; uint32_t n = 0;
        uint32_t maxc = (uint32_t)(tw / cw) - 1; if (maxc > 60) maxc = 60; if (maxc < 4) maxc = 4;
        const char *nm = str(Q->shortname);
        char pct[6]; uint32_t pn = 0; uint32_t v = P->pct[k];
        lab[n++] = ' '; lab[n++] = ' ';                           /* room for the colour swatch */
        if (k == st.tab) lab[n++] = '>';
        if (v >= 100) pct[pn++] = '1', pct[pn++] = '0', pct[pn++] = '0';
        else { if (v >= 10) pct[pn++] = (char)('0' + v / 10); pct[pn++] = (char)('0' + v % 10); }
        pct[pn++] = '%';
        uint32_t room = maxc > pn + 1 + n ? maxc - pn - 1 - n : 0;
        for (uint32_t i = 0; nm[i] && i < room; i++) lab[n++] = nm[i];
        lab[n++] = ' ';
        for (uint32_t i = 0; i < pn; i++) lab[n++] = pct[i];
        Rect b = { x + (tw + 8.0f) * (float)k, y, tw, bh };
        SV s = { n, lab };
        if (button(ui, &b, &s, 0) && st.tab != k) { st.tab = k; st.page = 0; }
        float sw[4];
        colour_of(Q->colour, 1.0f, sw);
        Rect sq = { b.x + 5.0f, b.y + (b.h - 10.0f) * 0.5f, 10.0f, 10.0f };
        fill(ui, &sq, sw);
    }
    y += lh + 12.0f;
    record(t, button, ui, G, x, y, w, ymax, lh, cw, col_text, col_dim);
}
