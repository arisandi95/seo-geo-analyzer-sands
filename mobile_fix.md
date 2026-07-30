# Update Log: Mobile Responsive Improvements

**Tanggal:** 2026-07-23  
**Issue:** Mobile kurang responsive + BMC button hilang

---

## 🔧 Fixed Issues

### 1. Buy Me a Coffee Button ✅
**Problem:** Button tidak muncul  
**Root cause:** `bmc_username = ""` (empty string)  
**Fix:** Set `bmc_username = "tosdwika"` di `base.html`

### 2. Mobile Responsive Improvements ✅

#### Global (style.css)
- Hero title mobile: 2.25rem → **2rem** (lebih compact)
- Hero subtitle mobile: tambah **0.9375rem** explicit size
- Section intro h2: tambah **1.75rem** mobile
- Feature cards: tambah **padding 24px** mobile
- Input group: tambah **gap 8px**, padding adjust
- Input button: tambah **padding 14px 20px** mobile
- Card padding: 24px → **20px** mobile
- Card title: tambah **1.125rem** mobile
- Navbar links: tambah **flex-wrap, gap 12px**
- Container: tambah **padding 0 16px** mobile
- Footer: 80px → **48px padding** mobile
- Tablet h1: 3.5rem → **3rem** (lebih proporsional)

#### Compare Page
- Page hero: **padding 32px 0 24px**
- Title/subtitle: **2rem / 0.9375rem**
- Card padding: 24px → **20px**
- Compare inputs gap: 12px → **16px**
- VS pill: **width/height 40px, font 0.75rem**
- Submit button: **padding 14px 20px, font 0.9375rem**
- Loading: **padding 20px**
- Card header: **center + column** mobile
- Field label: **font 0.75rem**
- Field input (480px): **font 0.9375rem**

#### History Page
- Page hero: **padding 32px 0 24px**
- Title/subtitle: **2rem / 0.9375rem**
- Card URL: **font 0.875rem** mobile

---

## 📊 Before/After

### Mobile (< 768px)
| Element | Before | After |
|---------|--------|-------|
| Hero title | 2.25rem (36px) | 2rem (32px) |
| Hero subtitle | inherit | 0.9375rem (15px) |
| Feature card padding | 32px | 24px |
| Card padding | 24px | 20px |
| Footer padding | 80px | 48px |
| Nav links | rigid | flex-wrap |
| Input gap | none | 8px |

### Tablet (768-1024px)
| Element | Before | After |
|---------|--------|-------|
| Hero title | 3.5rem (56px) | 3rem (48px) |
| Section h2 | inherit | 2rem |

---

## ✅ Result

### Mobile Experience
- ✅ Text sizes lebih readable (tidak terlalu besar)
- ✅ Padding/spacing lebih compact
- ✅ Nav links wrap properly
- ✅ Form inputs proper sizing
- ✅ BMC button visible di nav + footer

### Tablet Experience
- ✅ Title sizes lebih proporsional
- ✅ 2-column grid optimal

---

## 🧪 Test Checklist

### Mobile (375px)
- [x] Hero title 32px (tidak overflow)
- [x] Feature cards 1 column, padding 24px
- [x] Input button full width
- [x] Nav links wrap
- [x] BMC button visible
- [x] Footer 48px padding
- [x] Container 16px padding

### Tablet (768px)
- [x] Hero title 48px
- [x] Feature cards 2 columns
- [x] Compare side-by-side

### Desktop (1280px+)
- [x] No changes (tetap optimal)

---

**Status:** ✅ Mobile responsive improved + BMC restored
