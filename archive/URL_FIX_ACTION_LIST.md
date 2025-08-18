# Sips and Steals URL Fix Action List

## Summary
Analysis of the restaurant database revealed **25 URLs requiring attention** across 4 priority levels. This document provides specific actions to fix each problematic URL.

---

## 🚨 CRITICAL ISSUES (3 restaurants) - **IMMEDIATE ACTION REQUIRED**
*These URLs are completely blocking scraping with 404/403 errors*

### 1. A5 Steakhouse
- **Current URL:** `https://www.a5denver.com/menu#menu=happy-hour`
- **Issue:** HTTP 404 (Page Not Found)
- **Action:** Test and update to working URL
- **Suggested URLs to test:**
  - `https://www.a5denver.com/menu/` (remove fragment)
  - `https://www.a5denver.com/`
  - `https://www.a5denver.com/menus/`
  - `https://www.a5denver.com/happy-hour/`

### 2. Osteria Marco
- **Current URL:** `https://www.bonannoconcepts.com/restaurant/osteria-marco/`
- **Issue:** HTTP 403 (Access Forbidden - likely blocking scrapers)
- **Action:** Find alternative domain or disable scraping
- **Suggested URLs to test:**
  - `https://osteria-marco.com/`
  - `https://www.osteria-marco.com/`
  - `https://osteria-marco.com/menu/`
  - `https://osteria-marco.com/happy-hour/`
- **Fallback:** Disable live scraping for this restaurant

### 3. 100% de Agave
- **Current URL:** `https://100deagave.com/happy-hour/`
- **Issue:** HTTP 404 (Page Not Found)
- **Action:** Test and update to working URL
- **Suggested URLs to test:**
  - `https://100deagave.com/` (remove happy-hour path)
  - `https://100deagave.com/menu/`
  - `https://100deagave.com/specials/`
  - `https://100deagave.com/drinks/`

---

## ⚠️ HIGH PRIORITY (3 restaurants) - **SECURITY ISSUES**
*These use insecure HTTP instead of HTTPS*

### 4. Rioja
- **Current URL:** `http://www.riojadenver.com/menus/happy-hour-cocktails/`
- **Issue:** Using HTTP instead of HTTPS
- **Action:** Update to HTTPS
- **New URL:** `https://www.riojadenver.com/menus/happy-hour-cocktails/`

### 5. 9th Door
- **Current URL:** `http://9thdoorcapitolhill.com/happyhour`
- **Issue:** Using HTTP instead of HTTPS
- **Action:** Update to HTTPS
- **New URL:** `https://9thdoorcapitolhill.com/happyhour`

### 6. Annette
- **Current URL:** `http://www.annettescratchtotable.com/patiomenu`
- **Issue:** Using HTTP instead of HTTPS
- **Action:** Update to HTTPS
- **New URL:** `https://www.annettescratchtotable.com/patiomenu`

---

## 📋 MEDIUM PRIORITY (1 restaurant) - **OPTIMIZATION ISSUES**
*These have structural problems affecting performance*

### 7. Vesper Lounge
- **Current URL:** `https://www.bonannoconcepts.com/restaurant/vesper-lounge/?fbclid=IwZXh0bgNhZW0CMTAAAR28QTw3V-iGWwsfqYyZ6S3WKw9Q8ul23dTn_373gNeQHQvAwjE6fqO0XGU_aem_SQYzAjAG9klx4hQzBx-yKA`
- **Issue:** Long URL with Facebook tracking parameters
- **Action:** Remove tracking parameters
- **New URL:** `https://www.bonannoconcepts.com/restaurant/vesper-lounge/`

---

## 🔧 LOW PRIORITY (18 restaurants) - **FRAGMENT NAVIGATION ISSUES**
*These use JavaScript-based navigation that may not work with basic scraping*

These restaurants use fragment-based URLs (`#menu=happy-hour`) which require special handling:

### 8-25. Fragment URL Issues
The following restaurants need scraper enhancement or alternative URLs:

1. **Jovanina's Broken Italian** - `https://jovanina.com/#menus`
2. **Urban Farmer** - `https://www.urbanfarmersteakhouse.com/denver-menus/#happy-hour`
3. **Tavernetta** - `https://www.tavernettadenver.com/menus/#happy-hour`
4. **Sunday Vinyl** - `https://www.sundayvinyl.com/menus/#happy-hour`
5. **Mercantile** - `https://www.mercantiledenver.com/menus/#happy-hour`
6. **Wonderyard Garden + Table** - `https://www.wonderyard.com/menu#menu=specials`
7. **Shells and Sauce** - `https://www.shellsandsauce.net/menus/#happy-hour`
8. **Black+Haus Tavern - Littleton** - `https://www.blackhaustavern.com/menu-littleton#menu=happy-hour-sync`
9. **Jax Fish House** - `https://www.jaxfishhouse.com/location/jax-fish-house-oyster-bar-boulder/#happy-hour`
10. **My Neighbor Felix** - `https://www.myneighborfelix.com/location-boulder#menu=happy-hour`
11. **Olive & Finch** - `https://www.oliveandfinch.com/location/olive-finch-cherry-creek/#happy-hour-cherry-creek`
12. **Le French DTC Belleview Station** - `https://www.lefrenchdenver.com/le-french-dtc-belleview-station-menus/#happy-hour`
13. **Bar Dough** - `https://www.bardoughdenver.com/menu#menu=apertivo-hour-ordering`
14. **Kawa Ni** - `https://www.kawanidenver.com/#menu`
15. **Ash'Kara** - `https://www.ashkaradenver.com/menu#menu=happy-hour`
16. **Senor Bear** - `https://www.senorbeardenver.com/menu#menu=happy-hour`
17. **Tacos Tequila Whiskey** - `https://www.tacostequilawhiskey.com/dine-in-menu/#happy_hour`
18. **Reiver's Bar & Grill** - `https://www.reiversbarandgrill.com/menu#menu=happy-hour`

**Recommended Actions for Fragment URLs:**
- **Option A:** Remove fragments and test base URLs (e.g., `https://jovanina.com/` instead of `https://jovanina.com/#menus`)
- **Option B:** Enhance scraper to handle JavaScript-based navigation
- **Option C:** Find alternative menu/happy-hour pages without fragments

---

## Implementation Steps

### Phase 1: Critical Fixes (Immediate)
1. Test alternative URLs for A5 Steakhouse, Osteria Marco, and 100% de Agave
2. Update `data/restaurants.json` with working URLs
3. Verify scraping works for updated URLs

### Phase 2: Security Fixes (Week 1)
1. Update HTTP URLs to HTTPS for Rioja, 9th Door, and Annette
2. Test HTTPS connections work properly

### Phase 3: Optimization (Week 2)
1. Clean Vesper Lounge URL by removing tracking parameters
2. Test fragment URLs by removing fragments

### Phase 4: Fragment Enhancement (Week 3-4)
1. Analyze which fragment URLs work without fragments
2. Enhance scraper to handle JavaScript navigation if needed
3. Find alternative URLs for problematic fragment-based sites

---

## Success Metrics
- **Critical:** 3/3 dead links fixed (100% success rate)
- **High Priority:** 3/3 HTTP->HTTPS conversions (100% security compliance)
- **Medium Priority:** 1/1 URL optimized (reduced load time)
- **Low Priority:** Target 12+/18 fragment URLs working (67%+ success rate)

**Total Target:** 19+/25 URLs fixed (76%+ overall success rate)