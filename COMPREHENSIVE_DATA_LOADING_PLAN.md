# Comprehensive Data Loading Plan for Alabama Auction Watcher

**Objective:** To systematically and comprehensively scrape, parse, and import property data for all 67 counties in Alabama into the application's database.

**Context:** The application requires a robust and complete dataset to be useful. This plan outlines the process to populate the database with property data from all available counties. The process is designed to be executed sequentially and can be automated or followed manually by an AI.

---

### **Prerequisites**

1.  **Environment Setup:** Ensure the project environment is correctly set up with all dependencies installed.
2.  **Backend API:** The backend API must be running to handle the data import. If it is not running, start it with the following command in a separate terminal:
    ```bash
    python start_backend_api.py
    ```

---

### **Step-by-Step Data Loading Process**

This process should be repeated for each of the 67 counties in Alabama. A list of all counties is provided at the end of this document.

#### **Step 1: Scrape County Data**

This step scrapes the raw property data for a single county and saves it to a CSV file in the `data/raw` directory.

**Command Template:**
```bash
python scripts/parser.py --scrape-county "<COUNTY_NAME>" --max-pages <NUMBER_OF_PAGES>
```

**Instructions:**
*   Replace `<COUNTY_NAME>` with the name of the county you are scraping (e.g., "Autauga", "Baldwin").
*   Replace `<NUMBER_OF_PAGES>` with a high number to ensure all properties are scraped. A value of `100` is recommended to be safe, as the scraper will automatically stop when it runs out of pages.

**Example for Autauga County:**
```bash
python scripts/parser.py --scrape-county "Autauga" --max-pages 100
```

#### **Step 2: Import the Data**

After the parser script finishes (which now automatically scrapes and parses), this second command will import the newly processed data from `data/processed/watchlist.csv` into the database.

**Command:**
```bash
python scripts/import_data.py
```

---

### **Comprehensive Scrape Plan for All Counties**

To populate the entire database, the two steps above must be executed for all 67 counties in Alabama. It is recommended to run these commands sequentially for each county to avoid any potential conflicts.

**List of Alabama Counties:**
1.  Autauga
2.  Baldwin
3.  Barbour
4.  Bibb
5.  Blount
6.  Bullock
7.  Butler
8.  Calhoun
9.  Chambers
10. Cherokee
11. Chilton
12. Choctaw
13. Clarke
14. Clay
15. Cleburne
16. Coffee
17. Colbert
18. Conecuh
19. Coosa
20. Covington
21. Crenshaw
22. Cullman
23. Dale
24. Dallas
25. DeKalb
26. Elmore
27. Escambia
28. Etowah
29. Fayette
30. Franklin
31. Geneva
32. Greene
33. Hale
34. Henry
35. Houston
36. Jackson
37. Jefferson
38. Lamar
39. Lauderdale
40. Lawrence
41. Lee
42. Limestone
43. Lowndes
44. Macon
45. Madison
46. Marengo
47. Marion
48. Marshall
49. Mobile
50. Monroe
51. Montgomery
52. Morgan
53. Perry
54. Pickens
55. Pike
56. Randolph
57. Russell
58. St. Clair
59. Shelby
60. Sumter
61. Talladega
62. Tallapoosa
63. Tuscaloosa
64. Walker
65. Washington
66. Wilcox
67. Winston
