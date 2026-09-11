TEKGLIDE EXACT-URL GOOGLE RANK TRACKER - VERSION 10
===================================================

WHAT IT DOES
- 35 approved keywords targets.csv se read karta hai.
- Google US parameters (hl=en, gl=us, pws=0) use karta hai.
- Sponsored ads ignore karta hai.
- Sirf approved exact landing URL ko match karta hai; random Tekglide blog ignore hota hai.
- Maximum 10 Google pages check karta hai.
- rank_results.csv mein date, time, position, page, title aur URL save karta hai.

LOCAL WEB APP
- Local Flask interface one keyword at a time check karta hai.
- App sirf 127.0.0.1 par available hai; Chrome/Selenium job button click ke baad hi start hoti hai.
- run_local_app.bat double-click karein; browser automatically http://127.0.0.1:5000/ kholega.
- Flask page responsive rahega jab Selenium visible Chrome mein kaam karega.

HOW TO RUN
1. ZIP ko Extract All karein.
2. ExpressVPN USA - New York connect karein.
3. run_tracker.bat double-click karein.
4. First run par Selenium install hoga; baad ke runs par dobara install nahi hoga.
5. CAPTCHA aaye to Chrome mein manually solve karein. Chrome window band na karein.
6. Run complete hone par rank_results.csv isi folder mein milegi.

IMPORTANT
- Google rankings session, location, time, device aur personalization se change ho sakti hain.
- Automated Chrome aur aapke personal Chrome mein result order different ho sakta hai.
- Tool CAPTCHA bypass nahi karta.
- Hundreds of automated Google searches CAPTCHA/IP blocks trigger kar sakti hain. Slow testing karein.
- targets.csv ko Excel mein edit/save kiya ja sakta hai. Headers keyword,target_url same rakhein.

TEST FIRST
Single-keyword test mode targets.csv ko change nahi karta. Project folder mein PowerShell khol kar run karein:

	.venv\Scripts\python.exe rank_tracker.py --test-wix

Ya run_tracker.bat ko argument ke saath run karein:

	run_tracker.bat --test-wix

Kisi bhi ek keyword ko targets.csv se read karke test karne ke liye:

	.venv\Scripts\python.exe rank_tracker.py --test-keyword "SEO Consulting Services" --pause-after-found

Test keyword: Wix Development Agency
Expected target: https://tekglide.com/wix-development/
Chrome mein CAPTCHA aaye to manually solve karein. Test output mein har detected organic card is format mein aayega:

	Position | Title | URL | Ad status

Found result ko center/highlight karke Chrome khula rakhne ke liye:

	.venv\Scripts\python.exe rank_tracker.py --test-wix --pause-after-found

Terminal mein Enter dabane ke baad Chrome close hoga.

Test mein exact target FOUND hone ke baad hi normal full run karein:

	.venv\Scripts\python.exe rank_tracker.py

`--self-test` Chrome khole bina URL normalization checks chalata hai:

	.venv\Scripts\python.exe rank_tracker.py --self-test

Zero organic cards milne par diagnostics/ mein complete HTML, screenshot aur JSON diagnostics save hote hain. JSON mein page URL/title, selector counts, all anchor URLs aur available data-rank values hote hain.
