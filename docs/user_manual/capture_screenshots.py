from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import json
ROOT=Path(r'C:\Users\Administrator\Downloads\TechPulse-main (4)\TechPulse-main\docs\user_manual\screenshots')
ANN=ROOT/'annotated'; ROOT.mkdir(parents=True,exist_ok=True); ANN.mkdir(parents=True,exist_ok=True)
items=[]
def go(page,nav,title):
    link=page.get_by_role('link',name=nav)
    href=link.get_attribute('href')
    page.goto(href,wait_until='domcontentloaded',timeout=15000)
    for _ in range(60):
        current=page.locator('main').inner_text()
        if title in current:
            page.wait_for_timeout(250)
            return
        page.wait_for_timeout(250)
    raise RuntimeError(f'Navigation did not render {title}; current={page.locator("main").inner_text()[:250]!r}')

def go_click(page,nav,title):
    old=page.locator('main').inner_text()
    page.get_by_role('link',name=nav).click(timeout=10000)
    for _ in range(60):
        current=page.locator('main').inner_text()
        if current!=old and title in current:
            page.wait_for_timeout(1200); return
        page.wait_for_timeout(250)
    raise RuntimeError(f'Navigation did not render {title}; current={page.locator("main").inner_text()[:250]!r}')

def capture(page,name,caption,notes,scroll=None):
    if isinstance(scroll, int):
        page.locator('main').evaluate('(e,y)=>e.scrollTo(0,y)', scroll)
        page.wait_for_timeout(500)
    elif scroll:
        page.locator(scroll).scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(500)
    else:
        page.locator('main').evaluate('(e)=>e.scrollTo(0,0)')
        page.wait_for_timeout(350)
    path=ROOT/(name+'.png')
    page.screenshot(path=str(path),full_page=False,animations='disabled')
    im=Image.open(path).convert('RGB')
    d=ImageDraw.Draw(im)
    fontpath=r'C:\Windows\Fonts\arialbd.ttf'
    font=ImageFont.truetype(fontpath,30)
    # Margin badges do not cover the interface; letter key appears in a bottom annotation strip.
    band=82
    annotated=Image.new('RGB',(im.width,im.height+band),'#f5f0e8')
    annotated.paste(im,(0,0))
    d=ImageDraw.Draw(annotated)
    d.line((0,im.height,im.width,im.height),fill='#8c3545',width=4)
    # Stable letter markers identify navigation, mode, and primary page content.
    for letter,x,y,tx,ty in [('A',16,70,190,90),('B',16,735,190,780),('C',455,70,540,190)]:
        d.line((x+21,y+21,tx,ty),fill='#f1c56a',width=4)
        d.ellipse((x,y,x+42,y+42),fill='#8c3545',outline='#fff4df',width=3)
        box=d.textbbox((0,0),letter,font=font)
        d.text((x+21-(box[2]-box[0])/2,y+21-(box[3]-box[1])/2-2),letter,fill='white',font=font)
    label='A Sidebar navigation  |  B Data mode selector  |  C Current page title and content'
    d.text((24,im.height+10),label,fill='#292523',font=font)
    small=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',20)
    d.text((24,im.height+48),'Synthetic data unless the page identifies RESEARCH MODE.',fill='#6f5a50',font=small)
    out=ANN/(name+'_annotated.png')
    annotated.save(out,optimize=True)
    items.append({'name':name,'caption':caption,'notes':notes,'file':str(path),'annotated':str(out)})
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',args=['--disable-gpu','--no-sandbox'])
    page=browser.new_page(viewport={'width':1600,'height':1100},device_scale_factor=1.25)
    page.goto('http://localhost:8502',wait_until='networkidle',timeout=30000)
    page.wait_for_timeout(1200)
    page.wait_for_timeout(500)
    capture(page,'01_command_center','Figure 1.1. Synthetic Command Center. A: page navigation. B: synthetic scope banner. C: coverage metrics and class chart.', ['The page shows fictional catalogue counts and synthetic model metrics. It reports zero research predictions.'])
    go_click(page,'Technology Explorer','Technology Explorer')
    capture(page,'02_technology_explorer','Figure 5.1. Technology Explorer. A: search field. B: category filter. C: result table.', ['The default table is a fictional synthetic catalogue.'])
    page.get_by_label('Search fictional technologies').fill('DemoLang'); page.wait_for_timeout(700)
    capture(page,'03_explorer_search_results','Figure 5.2. Search result for DemoLang. A: exact text filter. B: filtered result. C: profile preview.', ['Search uses case-insensitive literal text; no match displays a helpful empty state.'])
    go(page,'Technology Profile','Technology Profile')
    capture(page,'04_technology_profile_overview','Figure 5.3. Technology Profile. A: selected fictional technology. B: synthetic label. C: monthly activity history.', ['The chart and label are generated demonstration outputs.'])
    capture(page,'05_profile_features','Figure 5.4. Seven feature values. A: Health Score. B: Growth Momentum Index. C: question and enterprise measures.', ['Read values using the nearby units. These demo formulae are not approved empirical definitions.'], 950)
    # scroll to prediction controls where possible
    page.locator('main').evaluate('(e)=>e.scrollTo(0,1050)'); page.wait_for_timeout(500)
    capture(page,'06_profile_predictions','Figure 5.5. Synthetic profile inference. A: model selector. B: generated class. C: class score table.', ['There is no separate live prediction-generation page; this saved inference is attached to the selected synthetic profile.'])
    go(page,'Global Rankings','Global Rankings')
    capture(page,'07_global_rankings','Figure 6.1. Global Rankings. A: metric selector. B: category filter. C: ranked result. D: CSV download.', ['Ranks describe the internally consistent synthetic scenario, not real-world technology leadership.'])
    go_click(page,'Community Health','Community Health')
    capture(page,'08_community_health','Figure 7.1. Community Health. A: fictional technology selector. B: generated activity timeline. C: discussion sample.', ['No generated post is a real Stack Overflow post or research observation.'])
    go(page,'Enterprise Adoption','Enterprise Adoption')
    capture(page,'09_enterprise_adoption','Figure 8.1. Enterprise Adoption. A: technology filter. B: sector filter. C: organization search. D: synthetic records.', ['Company names and relationships are fabricated examples, explicitly not verified adoption evidence.'])
    go(page,'Developer Sentiment','Developer Sentiment')
    capture(page,'10_developer_sentiment','Figure 8.2. Developer Sentiment. A: technology selector. B: measure selector. C: generated time series.', ['The monthly values and sample counts are simulated, not survey responses.'])
    go(page,'Kenya Landscape','Kenya Technology Landscape')
    capture(page,'11_kenya_landscape','Figure 9.1. Kenya-labelled synthetic scenarios. A: explicit warning. B: location filter. C: exported scenario rows.', ['These are invented Kenya-labelled examples; the research database has no verified Kenya-specific technology observations.'])
    go(page,'Model Laboratory','Model Laboratory')
    capture(page,'12_model_laboratory','Figure 10.1. Model Laboratory. A: retraining action. B: metric selector. C: model selector. D: aggregate scores.', ['Four saved synthetic model runs are displayed. Use class-level metrics before interpreting aggregate scores.'])
    page.locator('main').evaluate('(e)=>e.scrollTo(0,1250)'); page.wait_for_timeout(400)
    capture(page,'13_model_class_metrics','Figure 10.2. Per-class evaluation and confusion matrix. A: class precision/recall/F1. B: confusion matrix. C: CV folds.', ['Declining recall is low on this imbalanced synthetic holdout.'])
    go(page,'Explainability','Explainability')
    capture(page,'14_explainability_global','Figure 11.1. Explainability overview. A: global mean absolute SHAP chart. B: synthetic scope warning.', ['This explanation is for a generated feature panel and synthetic Random Forest only.'])
    # later page scroll to per-technology SHAP
    page.locator('main').evaluate('(e)=>e.scrollTo(0,1100)'); page.wait_for_timeout(400)
    capture(page,'15_explainability_local','Figure 11.2. Individual synthetic explanation. A: technology selector. B: local feature contributions.', ['Feature contributions are model associations, not causes.'])
    go(page,'Data Observatory','Data Observatory')
    capture(page,'16_data_observatory','Figure 12.1. Data Observatory. A: synthetic table counts. B: source and seed audit records.', ['The page exposes generated lineage and table counts from the isolated SQLite store.'])
    go(page,'Methodology & About','Methodology & About')
    capture(page,'17_methodology','Figure 12.2. Methodology and feature definitions. A: seven synthetic formula descriptions. B: label-rule boundary.', ['The SRS research rule and demo label rule are visibly distinguished.'])
    # Switch to genuine Research mode using the mode selector.
    box=page.locator('[data-testid="stSidebar"] [role="combobox"]')
    box.click(); page.wait_for_timeout(250)
    opts=page.get_by_role('option').all_text_contents(); print('mode options',opts)
    page.get_by_role('option',name='Research data · PostgreSQL').click(); page.wait_for_timeout(1500)
    print('research pages',page.locator('main').inner_text()[:1000])
    page.wait_for_timeout(400)
    capture(page,'18_research_overview','Figure 2.1. Research-mode overview. A: PostgreSQL status. B: real source coverage. C: prediction empty state.', ['This is genuine research mode. Counts describe recorded source coverage; the page says research predictions are not currently available.'])
    go_click(page,'Technology Rankings','Technology Rankings')
    capture(page,'20_research_rankings','Figure 6.2. Research rankings metric selector and evidence boundary.', ['The app withholds unsupported momentum values when the required time-aware community series is absent.'])
    go_click(page,'Community Health','Community Health')
    capture(page,'21_research_community_validation','Figure 7.2. Research community validation state. A: failed critical check. B: offending source evidence.', ['The two invalid cumulative Stack Exchange rows block ingestion rather than being silently removed.'])
    go_click(page,'Prediction Explorer','Prediction Explorer')
    capture(page,'22_research_prediction_empty','Figure 11.3. Research Prediction Explorer. A: accurate message when no valid model run and feature snapshot exist.', ['No research predictions are persisted; the warning is an intentional empty state.'])
    go_click(page,'Model Performance','Model Performance')
    capture(page,'23_research_model_empty','Figure 10.3. Research Model Performance. A: no valid PostgreSQL research run.', ['Historical fixtures and synthetic demo scores are excluded from current research results.'])
    go_click(page,'Data Provenance and Quality','Data Provenance and Quality')
    capture(page,'24_research_provenance','Figure 12.3. Research Data Provenance and Quality. A: source registry. B: canonical row estimates. C: blocked-source record.', ['The app is showing PostgreSQL provenance and status, not local synthetic SQLite rows.'])
    go_click(page,'Market and Skills Signals','Market and Skills Signals')
    capture(page,'25_research_market_signals','Figure 13.1. Research survey and skills view. A: year. B: geography. C: global-vs-Kenya evidence boundary.', ['Global/unspecified survey information is not presented as Kenya-specific behavior; no verified training/job evidence is reported.'])
    go_click(page,'Live Technology Intelligence','Live Technology Intelligence')
    capture(page,'26_research_live_empty','Figure 13.2. Research live-intelligence empty state. A: explicit message when no live observations are recorded.', ['No live technology observations are recorded in PostgreSQL.'])
    go_click(page,'About and Responsible Use','About and Responsible Use')
    capture(page,'27_research_responsible_use','Figure 13.3. Research interpretation and responsible-use notes.', ['The page distinguishes observations, derived measures, missing evidence, predictions, and limits.'])
    go_click(page,'Technology Explorer','Technology Explorer')
    page.get_by_label('Search technologies').fill('Python'); page.wait_for_timeout(1500)
    capture(page,'19_research_technology_search','Figure 5.6. Research technology search. A: canonical name search. B: stored evidence and prediction status.', ['Searches the canonical PostgreSQL technology catalogue. Missing evidence remains unavailable.'])
    browser.close()
(ROOT.parent/'screenshot_manifest.json').write_text(json.dumps(items,indent=2),encoding='utf-8')
print('captured',len(items),'screenshots; annotated',sum(Path(x['annotated']).exists() for x in items))
