#!/usr/bin/env python3
"""Generate the full cross-linked USA TODAY-style demo site.
Every page shares the same chrome (promo strip, nav, ads, sidebar, footer);
every nav item, promo tile, story thumbnail and sidebar item links to a real
page in this site, and every ad links out to the real brand.
Run:  python3 build.py   (from the site/ directory)
"""
import pathlib

# ---------------------------------------------------------------- CSS (verbatim)
CSS = r"""
    :root{
      --brand:#009bdf;        /* USA TODAY cyan-blue logo/buttons */
      --link:#0b6ea8;         /* article body links */
      --ink:#1a1a1a;
      --gray:#5a5a5a;
      --line:#e2e2e2;
      --nav:#2b2b2b;
      --band:#f4f4f4;
      --tileblue:#1f6fd0; --tilered:#e0362c; --tilepurple:#8b3ff2; --tilegreen:#2fa84f;
      --serif:Georgia,"Times New Roman",serif;
      --sans:"Helvetica Neue",Arial,sans-serif;
    }
    *{box-sizing:border-box}
    html,body{margin:0;padding:0}
    body{font-family:var(--sans);color:var(--ink);background:#fff;-webkit-font-smoothing:antialiased}
    a{color:var(--link);text-decoration:none}
    a:hover{text-decoration:underline}
    svg{display:block}
    .promo{border-bottom:1px solid var(--line);background:#fff}
    .promo-inner{max-width:1200px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:26px;flex-wrap:wrap}
    .logo{display:flex;align-items:center;gap:10px;text-decoration:none}
    .logo .dot{width:34px;height:34px;border-radius:50%;background:var(--brand)}
    .logo .txt{font-weight:800;font-size:20px;line-height:.95;letter-spacing:.5px;color:var(--ink)}
    .promo-item{font-size:13px;line-height:1.2;text-decoration:none;color:var(--ink)}
    .promo-item:hover .val{text-decoration:underline}
    .promo-item .lbl{color:var(--gray);font-weight:700;font-size:11px;letter-spacing:.5px}
    .promo-item .val{font-weight:700;font-size:15px}
    .promo-item .bar{height:3px;border-radius:2px;margin-bottom:6px}
    .b-blue{background:var(--tileblue)}.b-red{background:var(--tilered)}.b-purple{background:var(--tilepurple)}.b-green{background:var(--tilegreen)}
    .promo-cup{margin-left:auto;text-align:right;text-decoration:none}
    .promo-cup .t{color:var(--brand);font-weight:800;font-size:15px}
    .promo-cup .s{color:var(--gray);font-size:12px}
    nav.main{background:var(--nav);color:#fff;position:sticky;top:0;z-index:40}
    nav.main .row{max-width:1200px;margin:0 auto;padding:0 20px;display:flex;align-items:center;gap:22px;height:48px}
    nav.main a{color:#fff;font-weight:700;font-size:15px}
    nav.main .spacer{flex:1}
    nav.main .temp{font-weight:700}
    nav.main .pill{background:var(--brand);color:#fff;padding:7px 16px;border-radius:4px;font-weight:800}
    nav.main .signin{font-weight:800}
    .wrap{max-width:1200px;margin:0 auto;padding:0 20px;display:flex;gap:40px}
    main.content{flex:1;min-width:0;max-width:720px;padding:26px 0 50px}
    aside.rail{width:320px;flex:0 0 320px;padding:26px 0 50px}
    @media(max-width:980px){.wrap{flex-direction:column}aside.rail{width:100%;flex:none}}
    .ad-label{text-align:center;color:#9a9a9a;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin:14px 0 6px}
    .kicker-row{display:flex;justify-content:space-between;align-items:center;margin:8px 0 14px;flex-wrap:wrap;gap:10px}
    .kicker{color:var(--brand);font-weight:800;font-size:12px;letter-spacing:1px}
    .topic{display:flex;align-items:center;gap:12px}
    .topic .name{font-weight:700;font-size:14px}
    .add-topic{background:var(--brand);color:#fff;border:none;border-radius:20px;padding:6px 14px;font-weight:700;font-size:13px;cursor:pointer}
    h1.headline{font-family:var(--serif);font-size:40px;line-height:1.12;font-weight:700;margin:6px 0 22px}
    .byline{display:flex;align-items:center;gap:12px}
    .avatar{width:46px;height:46px;border-radius:50%;overflow:hidden;flex:0 0 auto;background:#c9d3da}
    .byline .who{display:flex;flex-direction:column;line-height:1.3}
    .author{color:var(--ink);font-weight:700}
    .org{font-family:var(--serif);font-style:italic;color:var(--gray);font-size:14px}
    .timestamp{color:var(--gray);font-size:14px;margin:12px 0 14px}
    .share{display:flex;gap:10px;padding-bottom:20px;border-bottom:1px solid var(--line)}
    .share span{width:34px;height:34px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line);color:var(--gray);font-weight:700;font-size:14px}
    figure{margin:24px 0}
    figure svg,figure img{width:100%;border-radius:2px}
    figcaption{color:var(--gray);font-size:13px;margin-top:8px;line-height:1.4}
    .ai{margin:24px 0;padding:20px;border-radius:12px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(0,155,223,.07),rgba(0,155,223,.02))}
    .ai .h{display:flex;align-items:center;gap:8px;margin-bottom:10px}
    .ai .h b{font-size:16px}.ai .h i{color:var(--gray);font-style:normal}
    .ai .lead{font-family:var(--serif);font-size:17px;margin:0 0 14px}
    .ai .lead .full{color:var(--ink);font-weight:700;white-space:nowrap}
    .ai ul{list-style:none;margin:0 0 16px;padding:0}
    .ai li{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 4px;border-top:1px solid var(--line)}
    .ai li a{color:var(--ink);font-weight:500}
    .ai .dd{display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid var(--line);border-radius:30px;background:rgba(127,127,127,.06)}
    .ai .dd .bd{font-weight:800}
    .ai .dd .beta{font-size:10px;font-weight:700;border:1px solid var(--gray);border-radius:10px;padding:1px 6px;color:var(--gray);margin-left:6px}
    .ai .dd .ph{color:var(--gray);flex:1;border-left:1px solid var(--line);padding-left:12px}
    .ai .dd .go{width:30px;height:30px;border-radius:50%;background:var(--brand);color:#fff;display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto}
    .body{font-family:var(--serif);font-size:19px;line-height:1.7}
    .body p{margin:0 0 20px}
    .body h2{font-family:var(--serif);font-size:25px;font-weight:700;margin:30px 0 16px}
    .body .note{color:var(--gray);font-style:italic}
    .more-grid h3{font-family:var(--serif);font-size:24px;margin:36px 0 16px;border-bottom:2px solid var(--brand);padding-bottom:8px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}
    @media(max-width:560px){.grid{grid-template-columns:1fr}}
    .card img{width:100%;border-radius:2px;aspect-ratio:17/10;object-fit:cover;display:block}
    .card .cat{color:var(--brand);font-weight:800;font-size:11px;letter-spacing:.5px;margin:8px 0 4px}
    .card .ttl{font-family:var(--serif);font-size:18px;font-weight:700;line-height:1.25}
    .card .ttl a{color:var(--ink)}
    .rail-sticky{position:sticky;top:64px}
    .fin-card{border:1px solid var(--line);border-top:none;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:14px;background:#fff;text-decoration:none;color:var(--ink)}
    .fin-card:first-of-type{border-top:1px solid var(--line)}
    .fin-card:hover{background:#fafafa;text-decoration:none}
    a.ad-link{display:block;cursor:pointer;text-decoration:none}
    a.ad-link:hover{filter:brightness(1.03);text-decoration:none}
    .fin-apy{font-size:30px;font-weight:800;line-height:1}
    .fin-apy sup{font-size:13px}
    .fin-sub{font-size:12px;color:var(--gray)}
    .fin-btn{background:var(--brand);color:#fff;border:none;border-radius:20px;padding:9px 16px;font-weight:800;font-size:13px;cursor:pointer;white-space:nowrap}
    .disc{text-align:center;color:var(--gray);font-size:11px;margin-top:8px}
    .story-mini{display:flex;gap:12px;padding:14px 0;border-top:1px solid var(--line);align-items:center;text-decoration:none;color:var(--ink)}
    .story-mini:hover .m-ttl{text-decoration:underline}
    .story-mini img{width:96px;height:64px;flex:0 0 auto;border-radius:2px;object-fit:cover}
    .story-mini .m-ttl{font-family:var(--serif);font-weight:700;font-size:16px;line-height:1.25}
    .story-mini .m-cat{color:var(--gray);font-size:11px;font-weight:700;letter-spacing:.5px;margin-top:4px}
    .games-box{background:#242424;color:#fff;padding:20px;margin-top:24px}
    .games-box h4{margin:0 0 8px;font-size:20px}
    .games-box p{margin:0 0 12px;font-size:14px;color:#cfcfcf}
    .games-box .inp{display:flex;border:1px solid #555;background:#333}
    .games-box .inp input{flex:1;background:transparent;border:none;color:#fff;padding:10px 12px;font-size:13px}
    .games-box .inp button{background:#555;color:#fff;border:none;padding:0 14px;font-weight:800}
    footer.site{background:var(--nav);color:#ccc;margin-top:30px}
    footer.site .f{max-width:1200px;margin:0 auto;padding:26px 20px;font-size:13px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:14px}
    footer.site a{color:#9ecbff}
    @media(max-width:560px){h1.headline{font-size:29px}.promo-item,.promo-cup{display:none}}
"""

EXT = 'target="_blank" rel="noopener noreferrer sponsored"'

# ---------------------------------------------------------------- shared chrome
def head(title, desc):
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "  <meta charset=\"utf-8\" />\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
            f"  <title>{title} &mdash; USA TODAY</title>\n"
            f"  <meta name=\"description\" content=\"{desc}\" />\n"
            f"  <style>{CSS}  </style>\n</head>\n<body>\n")

def promo():
    return (
    '  <div class="promo"><div class="promo-inner">\n'
    '    <a class="logo" href="index.html"><span class="dot"></span><span class="txt">USA<br>TODAY</span></a>\n'
    '    <a class="promo-item" href="trump-accounts.html"><div class="bar b-blue"></div><span class="lbl">USA 250</span><br><span class="val">America&rsquo;s birthday &#127874;</span></a>\n'
    '    <a class="promo-item" href="messi-cape-verde.html"><div class="bar b-red"></div><span class="lbl">SCORES &amp; STATS</span><br><span class="val">World Cup mania &#127758; &#127942;</span></a>\n'
    '    <a class="promo-item" href="si-swimsuit.html"><div class="bar b-purple"></div><span class="lbl">ON USA TODAY PLAY</span><br><span class="val">Explore Marvel comics</span></a>\n'
    f'    <a class="promo-item" href="https://www.homes.com/" {EXT}><div class="bar b-green"></div><span class="lbl">REAL ESTATE LISTINGS</span><br><span class="val">Check home prices &#127968;</span></a>\n'
    '    <a class="promo-cup" href="messi-cape-verde.html"><div class="t">Inside the Cup</div><div class="s">Tournament pass</div></a>\n'
    '  </div></div>\n')

NAV_ITEMS = [
    ("U.S.", "index.html"), ("Politics", "supreme-court.html"),
    ("Sports", "messi-cape-verde.html"), ("Entertainment", "si-swimsuit.html"),
    ("Life", "drowning-safety.html"), ("Money", "tesla-evs.html"),
    ("Travel", "who-has-ac.html"), ("Opinion", "trump-accounts.html"),
    ("Crossword", "https://www.usatoday.com/crossword/"),
]
def nav():
    links = ""
    for label, href in NAV_ITEMS:
        ext = f" {EXT}" if href.startswith("http") else ""
        links += f'<a href="{href}"{ext}>{label}</a>'
    return (
    '  <nav class="main"><div class="row">\n'
    f'      {links}\n'
    '      <span class="spacer"></span>\n'
    '      <span class="temp">82&deg;F &#9728;</span>\n'
    f'      <a class="pill" href="https://www.usatoday.com/subscribe/" {EXT}>Subscribe</a>\n'
    f'      <a href="https://www.usatoday.com/" class="signin" {EXT}>Sign In &#9662;</a>\n'
    '  </div></nav>\n')

def lincoln():
    return (
    '  <div class="wrap" style="display:block">\n    <div class="ad-label">Advertisement</div>\n'
    f'    <a class="ad-link" href="https://www.lincoln.com/luxury-suvs/nautilus/" {EXT} title="2026 Lincoln Nautilus">\n'
    '    <svg viewBox="0 0 1160 360" width="100%" role="img" aria-label="2026 Lincoln Nautilus ad">\n'
    '      <rect width="1160" height="360" fill="#eef0ef"/>\n'
    '      <g font-family="Georgia,serif" fill="#2b3a3d">\n'
    '        <line x1="60" y1="96" x2="150" y2="96" stroke="#2b3a3d" stroke-width="2"/>\n'
    '        <line x1="470" y1="96" x2="560" y2="96" stroke="#2b3a3d" stroke-width="2"/>\n'
    '        <text x="175" y="102" font-size="24" letter-spacing="3" font-weight="bold">2026 LINCOLN NAUTILUS</text>\n'
    '        <text x="60" y="185" font-size="46" font-weight="bold">Stylish, Inside and Out</text>\n'
    '      </g>\n'
    '      <text x="60" y="230" font-family="Helvetica,Arial" font-size="18" fill="#3a4a4d">Design cues, both subtle and grand, combine</text>\n'
    '      <text x="60" y="256" font-family="Helvetica,Arial" font-size="18" fill="#3a4a4d">for a centered expression of style and motion.</text>\n'
    '      <rect x="60" y="290" width="480" height="46" fill="#2f3b40"/>\n'
    '      <g transform="translate(78,297)"><rect x="0" y="0" width="34" height="32" fill="none" stroke="#fff" stroke-width="1.4"/>\n'
    '        <polygon points="17,4 21,14 30,16 21,18 17,28 13,18 4,16 13,14" fill="#fff"/></g>\n'
    '      <line x1="128" y1="298" x2="128" y2="328" stroke="#6f7a7e" stroke-width="1"/>\n'
    '      <text x="142" y="318" font-family="Georgia,serif" font-size="15" letter-spacing="3" fill="#fff">SANDERSON LINCOLN</text>\n'
    '      <clipPath id="suvclip"><rect x="600" y="40" width="500" height="280" rx="6"/></clipPath>\n'
    '      <image href="images/ad-lincoln-suv.jpg" x="600" y="40" width="500" height="280" preserveAspectRatio="xMidYMid slice" clip-path="url(#suvclip)"/>\n'
    '    </svg>\n    </a>\n  </div>\n')

def espn():
    return (
    '      <div class="ad-label">Advertisement</div>\n'
    f'      <a class="ad-link" href="https://plus.espn.com/mlb" {EXT} title="ESPN+ MLB.TV">\n'
    '      <svg viewBox="0 0 720 150" width="100%" role="img" aria-label="ESPN MLB.TV ad">\n'
    '        <rect width="720" height="150" fill="#0b0b0b"/>\n'
    '        <g transform="translate(24,34)"><rect x="-4" y="-2" width="132" height="40" rx="3" fill="#e0271c"/>\n'
    '          <text x="62" y="27" text-anchor="middle" font-family="Arial" font-weight="900" font-style="italic" font-size="27" fill="#fff" letter-spacing="1">ESPN</text></g>\n'
    '        <g transform="translate(24,86)"><rect width="40" height="46" rx="3" fill="#e0271c"/><rect x="0" width="20" height="46" rx="3" fill="#00318f"/>\n'
    '          <path d="M10 8 a4 4 0 1 1 0 .1 M8 16 l6 14 -3 12 M20 20 l10 -6" stroke="#fff" stroke-width="3" fill="none"/>\n'
    '          <text x="50" y="34" font-family="Arial" font-weight="900" font-size="22" fill="#fff">MLB.TV</text></g>\n'
    '        <text x="200" y="52" font-family="Arial" font-weight="900" font-style="italic" font-size="26" fill="#e0271c">ESPN IS THE HOME OF MLB.TV</text>\n'
    '        <text x="200" y="82" font-family="Arial" font-size="15" fill="#e8e8e8">Upgrade to an ESPN Unlimited Plan to add MLB.TV and</text>\n'
    '        <text x="200" y="104" font-family="Arial" font-size="15" fill="#e8e8e8">stream all out-of-market games, live or on demand.</text>\n'
    '        <rect x="560" y="52" width="130" height="40" rx="4" fill="#fff"/>\n'
    '        <text x="625" y="78" text-anchor="middle" font-family="Arial" font-weight="800" font-size="14" fill="#0b0b0b">SIGN UP NOW</text>\n'
    '      </svg>\n      </a>\n')

def nanit():
    return (
    '        <div class="ad-label">Advertisement</div>\n'
    f'        <a class="ad-link" href="https://www.nanit.com/" {EXT} title="Nanit baby monitors">\n'
    '        <svg viewBox="0 0 720 360" width="100%" role="img" aria-label="nanit baby monitor ad">\n'
    '          <defs><linearGradient id="ov" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="rgba(10,18,26,.85)"/>\n'
    '            <stop offset="0.55" stop-color="rgba(10,18,26,.45)"/><stop offset="1" stop-color="rgba(10,18,26,.15)"/></linearGradient></defs>\n'
    '          <image href="images/ad-nanit-baby.jpg" x="0" y="0" width="720" height="360" preserveAspectRatio="xMidYMid slice"/>\n'
    '          <rect width="720" height="360" fill="url(#ov)"/>\n'
    '          <rect x="16" y="14" width="42" height="22" rx="3" fill="rgba(0,0,0,.6)"/>\n'
    '          <text x="37" y="30" text-anchor="middle" font-family="Arial" font-size="12" fill="#fff">Ad</text>\n'
    '          <text x="52" y="150" font-family="Georgia,serif" font-size="42" fill="#f4f7f9">You can leave the</text>\n'
    '          <text x="52" y="200" font-family="Georgia,serif" font-size="42" fill="#f4f7f9">hovering to us</text>\n'
    '          <text x="690" y="342" text-anchor="end" font-family="Arial,Helvetica" font-weight="800" font-size="26" fill="#fff">nanit</text>\n'
    '        </svg>\n        </a>\n')

def sidebar(current):
    minis = ""
    for s in [S["nancy-guthrie"], S["si-swimsuit"], S["tesla-evs"]]:
        if s["slug"] == current:
            continue
        minis += (f'        <a class="story-mini" href="{s["file"]}">\n'
                  f'          <img src="images/{s["thumb"]}" alt="{s["hero_alt"]}" loading="lazy" />\n'
                  f'          <div><div class="m-ttl">{s["headline"]}</div><div class="m-cat">{s["cat"]}</div></div>\n'
                  f'        </a>\n')
    return (
    '    <aside class="rail"><div class="rail-sticky">\n'
    '        <div class="ad-label">Advertisement</div>\n'
    f'        <a class="fin-card" href="https://us.etrade.com/" {EXT}><div>\n'
    '            <svg viewBox="0 0 150 22" width="120" height="18" aria-label="E*TRADE"><text x="0" y="18" font-family="Arial" font-weight="900" font-size="20" fill="#00874d">E</text>\n'
    '              <polygon points="20,4 22,10 28,10 23,14 25,20 20,16 15,20 17,14 12,10 18,10" fill="#00a862" transform="scale(0.7) translate(9,3)"/>\n'
    '              <text x="26" y="18" font-family="Arial" font-weight="900" font-size="20" fill="#00874d">TRADE</text></svg>\n'
    '            <div class="fin-sub">from Morgan Stanley &middot; Member FDIC</div><div class="fin-apy">4.10<sup>% APY</sup></div><div class="fin-sub">12-Month Certificate of Deposit</div></div>\n'
    '          <span class="fin-btn">GET STARTED</span></a>\n'
    f'        <a class="fin-card" href="https://www.capitalone.com/bank/savings-accounts/online-performance-savings-account/" {EXT}><div>\n'
    '            <svg viewBox="0 0 150 24" width="120" height="20" aria-label="Capital One"><text x="0" y="19" font-family="Arial" font-weight="700" font-size="19" fill="#004977">Capital<tspan font-weight="400">One</tspan></text>\n'
    '              <path d="M2 4 q60 -8 120 4" stroke="#d03027" stroke-width="4" fill="none" stroke-linecap="round"/></svg>\n'
    '            <div class="fin-apy">3.00<sup>% APY</sup></div><div class="fin-sub">360 Performance Savings &middot; Member FDIC</div></div>\n'
    '          <span class="fin-btn">OPEN ACCOUNT</span></a>\n'
    f'        <a class="fin-card" href="https://www.sofi.com/banking/" {EXT}><div>\n'
    '            <svg viewBox="0 0 90 24" width="72" height="19" aria-label="SoFi"><text x="0" y="19" font-family="Arial" font-weight="800" font-size="20" fill="#00a0c6">SoFi</text></svg>\n'
    '            <div class="fin-sub">Checking &amp; Savings &middot; Member FDIC</div><div class="fin-apy">3.80<sup>% APY</sup></div><div class="fin-sub">+0.70% boost on new accounts</div></div>\n'
    '          <span class="fin-btn">START BANKING</span></a>\n'
    f'        <a class="fin-card" href="https://www.betterment.com/cash-reserve" {EXT}><div>\n'
    '            <svg viewBox="0 0 150 24" width="120" height="19" aria-label="Betterment"><circle cx="8" cy="12" r="7" fill="#0f2b46"/><path d="M4 12 a4 4 0 0 1 8 0z" fill="#f4b23e"/>\n'
    '              <text x="20" y="18" font-family="Arial" font-weight="700" font-size="18" fill="#0f2b46">Betterment</text></svg>\n'
    '            <div class="fin-sub">Cash Reserve &middot; New customer offer</div><div class="fin-apy">4.00<sup>% APY</sup></div></div>\n'
    '          <span class="fin-btn">CLAIM OFFER</span></a>\n'
    f'        <a class="disc" href="https://www.gobankingrates.com/" {EXT} style="display:block;text-decoration:none">Sponsors of GOBankingRates &middot; Advertiser Disclosure</a>\n'
    '        <div class="ad-label" style="margin-top:24px">Advertisement</div>\n'
    f'        <a class="ad-link" href="https://www.frontier.com/fiber-internet" {EXT} title="Frontier Fiber Internet">\n'
    '        <svg viewBox="0 0 320 300" width="100%" role="img" aria-label="Switch for 300 Mbps Fiber Internet"><rect width="320" height="300" fill="#0b57d0"/>\n'
    '          <text x="24" y="120" font-family="Arial" font-weight="900" font-size="30" fill="#fff">Switch for</text>\n'
    '          <text x="24" y="160" font-family="Arial" font-weight="900" font-size="34" fill="#fff">300 Mbps</text>\n'
    '          <text x="24" y="196" font-family="Arial" font-weight="900" font-size="30" fill="#fff">Fiber Internet</text>\n'
    '          <rect x="24" y="230" width="150" height="42" rx="21" fill="#fff"/><text x="99" y="257" text-anchor="middle" font-family="Arial" font-weight="800" font-size="15" fill="#0b57d0">Switch today</text></svg>\n        </a>\n'
    '        <div class="ad-label" style="margin-top:24px">Advertisement</div>\n'
    f'        <a class="story-mini" style="border-top:none" href="https://www.webmd.com/erectile-dysfunction/default.htm" {EXT}>\n'
    '          <img src="images/s-health.jpg" alt="Fitness" loading="lazy" />\n'
    '          <div><div class="m-ttl" style="font-size:15px">Why 110,000+ Men Over 40 Are Quietly Throwing Out Their Blue Pills</div><div class="m-cat">Peak Health Reviews | Ad</div></div>\n        </a>\n'
    '        <h3 style="font-family:var(--serif);font-size:22px;margin:26px 0 6px;border-bottom:2px solid var(--brand);padding-bottom:8px">More Stories</h3>\n'
    f'{minis}'
    '        <div class="games-box"><h4>PLAY a mix of games, in your inbox</h4>\n'
    '          <p>Your go-to spot where fun comes first with games, puzzles, comics, horoscopes and more!</p>\n'
    '          <div class="inp"><input type="email" placeholder="Email Address" aria-label="Email Address"/><button>&rarr;</button></div></div>\n'
    '    </div></aside>\n')

def banners_footer():
    return (
    '  <div class="wrap" style="display:block"><div class="ad-label">Advertisement</div>\n'
    f'    <a class="ad-link" href="https://www.amazon.com/" {EXT} title="Amazon">\n'
    '    <svg viewBox="0 0 1160 120" width="100%" role="img" aria-label="Amazon ad"><rect width="1160" height="120" fill="#0f1111"/>\n'
    '      <text x="40" y="55" font-family="Arial" font-weight="800" font-size="30" fill="#fff">60% of sales on Amazon come</text>\n'
    '      <text x="40" y="95" font-family="Arial" font-weight="800" font-size="30" fill="#fff">from independent sellers</text>\n'
    '      <g transform="translate(950,42)"><text x="0" y="30" font-family="Arial" font-weight="700" font-size="44" fill="#fff" letter-spacing="-1">amazon</text>\n'
    '        <path d="M6 44 q64 30 132 4" stroke="#ff9900" stroke-width="7" fill="none" stroke-linecap="round"/><path d="M138 48 l14 -6 -3 15 z" fill="#ff9900"/></g></svg>\n    </a>\n  </div>\n'
    '  <div class="wrap" style="display:block"><div class="ad-label">Advertisement</div>\n'
    f'    <a class="ad-link" href="https://www.max.com/" {EXT} title="HBO Max">\n'
    '    <svg viewBox="0 0 1160 90" width="100%" role="img" aria-label="HBO Max ad"><rect width="1160" height="90" fill="#0a0a0a"/>\n'
    '      <text x="40" y="40" font-family="Arial" font-weight="800" font-size="16" fill="#bbb" letter-spacing="1">STARTING AT</text>\n'
    '      <text x="40" y="72" font-family="Arial" font-weight="900" font-size="30" fill="#fff">$6.58<tspan font-size="16" fill="#bbb"> /MO WHEN YOU PREPAY FOR A YEAR</tspan></text>\n'
    '      <text x="1000" y="56" text-anchor="end" font-family="Arial" font-weight="900" font-size="26" fill="#fff">HBO <tspan fill="#7a5cff">max</tspan></text>\n'
    '      <text x="1120" y="56" text-anchor="end" font-family="Arial" font-size="13" fill="#9ecbff">on prime video</text></svg>\n    </a>\n  </div>\n'
    '  <footer class="site"><div class="f">\n'
    '      <div>&copy; 2026 USA TODAY, a division of Gannett Satellite Information Network, LLC. &nbsp;<em>(Demo layout, recreated for preview, not affiliated with USA TODAY.)</em></div>\n'
    '      <div><a href="index.html">Home</a> &middot; <a href="#">Terms</a> &middot; <a href="#">Privacy</a></div>\n'
    '  </div></footer>\n</body>\n</html>\n')

# ---------------------------------------------------------------- article + grid
def grid(current):
    order = ["supreme-court","who-has-ac","drowning-safety","trump-accounts",
             "iu-workforce","messi-cape-verde","tesla-evs","si-swimsuit","nancy-guthrie"]
    cards = ""
    n = 0
    for slug in order:
        if slug == current or n >= 6:
            continue
        s = S[slug]; n += 1
        cards += (f'          <div class="card"><a href="{s["file"]}"><img src="images/{s["thumb"]}" alt="{s["hero_alt"]}" loading="lazy" /></a>\n'
                  f'            <div class="cat">{s["cat"]}</div>\n'
                  f'            <div class="ttl"><a href="{s["file"]}">{s["headline"]}</a></div></div>\n')
    return ('      <div class="more-grid"><h3>More from USA TODAY</h3>\n'
            f'        <div class="grid">\n{cards}        </div></div>\n')

def article(s):
    qs = "".join(f'          <li><a href="#full">{q}</a><span>&rarr;</span></li>\n' for q in s["ai_q"])
    # body blocks, inject nanit after 2nd paragraph
    out = ""; pcount = 0; injected = False
    for kind, text in s["blocks"]:
        if kind == "p":
            out += f'        <p>{text}</p>\n'; pcount += 1
            if pcount == 2 and not injected:
                out += nanit(); injected = True
        elif kind == "h2":
            out += f'        <h2>{text}</h2>\n'
        elif kind == "note":
            out += f'        <p id="full" class="note">{text}</p>\n'
    if not injected:  # short article: still show the ad
        out += nanit()
    return (
    '    <main class="content">\n'
    f'      <div class="kicker-row"><span class="kicker">{s["kicker"]}</span>\n'
    f'        <div class="topic"><span class="name">{s["topic"]}</span><button class="add-topic">Add Topic +</button></div></div>\n'
    f'      <h1 class="headline">{s["headline"]}</h1>\n'
    '      <div class="byline"><span class="avatar"><img src="images/author-keith.jpg" alt="Staff" width="46" height="46" style="width:46px;height:46px;object-fit:cover" /></span>\n'
    f'        <div class="who"><a href="#" class="author">{s["author"]}</a><span class="org">{s["org"]}</span></div></div>\n'
    f'      <p class="timestamp">{s["date"]}</p>\n'
    '      <div class="share"><span>f</span><span>X</span><span>&#9993;</span><span>&#10150;</span></div>\n'
    '      <section class="ai"><div class="h"><b>AI Overview</b><i>&#9432;</i></div>\n'
    f'        <p class="lead">{s["ai_lead"]} <a href="#full" class="full">Full Summary</a></p>\n'
    f'        <ul>\n{qs}        </ul>\n'
    '        <div class="dd"><span class="bd">DeeperDive<span class="beta">BETA</span></span><span class="ph">Ask USA TODAY anything</span><span class="go">&rarr;</span></div></section>\n'
    f'      <figure><img src="images/{s["hero"]}" alt="{s["hero_alt"]}" loading="lazy" />\n'
    f'        <figcaption>{s["caption"]}</figcaption></figure>\n'
    f'{espn()}'
    '      <div class="body">\n'
    f'{out}'
    '      </div>\n'
    f'{grid(s["slug"])}'
    '    </main>\n')

def page(s):
    return (head(s["headline"], s["desc"]) + promo() + nav() + lincoln()
            + '  <div class="wrap">\n' + article(s) + sidebar(s["slug"])
            + '  </div>\n' + banners_footer())

# ---------------------------------------------------------------- content
def P(t): return ("p", t)
def H(t): return ("h2", t)
def N(t): return ("note", t)

S = {}
def add(**k): S[k["slug"]] = k

add(slug="index", file="index.html", kicker="RURAL SAFETY", topic="Iowa", cat="NEWS",
    headline="An Iowa farmer went out to his cattle pen and never came back. A black bull is to blame, the sheriff says",
    author="Keith Laing", org="USA TODAY", date="July 3, 2026, 9:14 a.m. ET",
    hero="lead-bull.jpg", thumb="lead-bull.jpg",
    hero_alt="A large bull in a pasture",
    caption="A bull in a herd on a family cattle operation. Authorities say a black bull fatally attacked a 68-year-old farmer near Harlan, Iowa. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="A 68-year-old Iowa farmer was killed by a black bull in his own cattle pen, the Shelby County Sheriff's Office says.",
    ai_lead="A 68-year-old farmer near Harlan, Iowa, was killed by a black bull in his own cattle pen, the Shelby County Sheriff&rsquo;s Office says, in an attack investigators describe as sudden and without documented warning.",
    ai_q=["How did the farmer&rsquo;s family find him?","What did the Shelby County Sheriff say about the bull?","How common are cattle-related deaths on U.S. farms?"],
    blocks=[
        P("HARLAN, Iowa. A routine evening chore on a family farm in western Iowa ended in tragedy this week when a 68-year-old farmer was fatally attacked by a black bull in his own cattle pen, authorities said."),
        P("Marvin E. Thompson was found dead in the pen on his property near Harlan after he failed to return to the house for supper on Monday evening, according to the Shelby County Sheriff&rsquo;s Office. His wife discovered him after he did not come in, deputies said."),
        P("Shelby County Sheriff Neil Gross said Thompson died from injuries caused by an attack from a large black bull that was part of the herd. Deputies secured the animal at the scene without further incident, the sheriff said."),
        P("&ldquo;This was a sudden and violent encounter with an animal these families work around every single day,&rdquo; the sheriff&rsquo;s office indicated in describing the case, which it characterized as the kind of routine farm work that turned deadly in an instant. Investigators said there were no immediate prior signs of aggression documented in the statements available to them."),
        P("The timeline released by deputies is stark in its ordinariness. Thompson went out to tend the herd, as he had countless times before. When he did not come back for the evening meal, his wife went looking, and found him in the pen with the bull still nearby."),
        P("The bull, an <a href=\"https://en.wikipedia.org/wiki/Angus_cattle\">Angus</a>, had no name. Production cattle rarely do. Unlike a family pet, animals raised as livestock are typically tracked by ear tag rather than named, a deliberate distance keepers keep from animals bound for market. It is a detail that underscores the nature of the work: this was not a companion animal, but one of the powerful production animals a farmer like Thompson handled as a matter of routine."),
        P("Authorities have not reported any indication that the bull had shown aggression toward Thompson or others before Monday, and no charges or further action against the animal have been announced. The bull remains secured following the events, the sheriff&rsquo;s office said."),
        H("A hidden hazard on America&rsquo;s farms"),
        P("The death is a reminder of a danger that rarely makes national headlines but is well known across farm country: bulls, which can weigh well over a ton, are among the most dangerous animals routinely handled on cattle operations. Agricultural-safety specialists have long warned that even docile, familiar animals can turn without warning, particularly in the close quarters of a pen."),
        P("For the community around Harlan, a town of a few thousand people roughly an hour northeast of Omaha, Nebraska, the loss lands close to home in a place where livestock work is part of daily life."),
        N("The Shelby County Sheriff&rsquo;s Office confirmed the black bull as the animal involved and said the investigation into the circumstances of Thompson&rsquo;s death is continuing. This is a developing story."),
    ])

add(slug="supreme-court", file="supreme-court.html", kicker="POLITICS", topic="Supreme Court", cat="POLITICS",
    headline="In a polarized Supreme Court, even its conservatives are divided on Trump",
    author="Maureen Groppe", org="USA TODAY", date="July 3, 2026, 3:01 a.m. ET",
    hero="t-supreme-court.jpg", thumb="t-supreme-court.jpg", hero_alt="U.S. Supreme Court building",
    caption="The U.S. Supreme Court in Washington. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="The Supreme Court's conservative majority has shown notable divisions in recent cases involving President Donald Trump.",
    ai_lead="The Supreme Court&rsquo;s conservative majority, often treated as a single bloc, has splintered on a series of recent cases touching President Donald Trump, from birthright citizenship to tariffs.",
    ai_q=["Which issues split the conservative justices?","Is the court really six-to-three in practice?","What cases are coming next term?"],
    blocks=[
        P("WASHINGTON. Conservatives dominate the Supreme Court, but they are not monolithic. Across a run of recent decisions involving President Donald Trump, the justices appointed by Republican presidents have repeatedly split from one another."),
        P("On questions ranging from birthright citizenship to tariffs, the conservative wing has divided over how far executive power reaches and how strictly to read the text of federal statutes."),
        P("Court watchers say the pattern complicates the popular assumption that a six-to-three conservative majority guarantees uniform outcomes. Concurrences and partial dissents have grown more common, exposing distinct judicial philosophies."),
        P("Those divisions are likely to shape the next term, when several cases touching on the limits of federal authority are expected to be argued."),
        N("This analysis is based on the court&rsquo;s published opinions from the term. The court&rsquo;s next term begins in October."),
    ])

add(slug="who-has-ac", file="who-has-ac.html", kicker="WEATHER", topic="Extreme Heat", cat="WEATHER",
    headline="Who doesn&rsquo;t have AC? Maps show the places that use it least",
    author="Doyle Rice", org="USA TODAY", date="July 3, 2026, 6:04 a.m. ET",
    hero="t-heat.jpg", thumb="t-heat.jpg", hero_alt="The sun during a heat wave",
    caption="A dangerous heat wave is gripping much of the country ahead of July 4. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="As a dangerous heat wave hits ahead of July 4, data shows which parts of the U.S. are least likely to have air conditioning.",
    ai_lead="As a dangerous heat wave settles over much of the country ahead of the July 4 holiday, data highlights which parts of the United States are least likely to have air conditioning.",
    ai_q=["Which regions have the least AC?","Why are mild-summer areas more vulnerable?","How can people stay safe in extreme heat?"],
    blocks=[
        P("Some parts of the nation have far more air conditioning than others, and a dangerous heat wave is drawing new attention to the gap just as millions head outdoors for Independence Day."),
        P("Nationwide, air conditioning is nearly universal across the South and much of the interior, where brutal summers are a given. But in cooler coastal and northern areas, a meaningful share of homes still go without."),
        P("Public health officials warn that regions with historically mild summers can be the most vulnerable during extreme heat, precisely because residents and housing stock are less prepared for it."),
        P("Experts advise checking on older neighbors, staying hydrated, limiting midday activity, and seeking out public cooling centers during the hottest hours."),
        N("Forecasters expect the heat to persist through the holiday weekend across the Midwest, South and East Coast."),
    ])

add(slug="drowning-safety", file="drowning-safety.html", kicker="HEALTH AND WELLNESS", topic="Water Safety", cat="HEALTH AND WELLNESS",
    headline="Their 6-year-old son drowned. Here&rsquo;s what they want families to know",
    author="Adrianna Rodriguez", org="USA TODAY", date="July 3, 2026, 8:11 a.m. ET",
    hero="t-boat.jpg", thumb="t-boat.jpg", hero_alt="A child on a boat on a lake",
    caption="Safety advocates urge layered protections around water. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="After losing their 6-year-old son to drowning, a family shares water-safety lessons they hope will spare others.",
    ai_lead="After losing their 6-year-old son to drowning, one family is speaking out in the hope their story spares other parents the same grief.",
    ai_q=["Why is drowning so hard to spot?","What safety layers do experts recommend?","How common is childhood drowning?"],
    blocks=[
        P("A family that lost their 6-year-old son to drowning is sharing their story, hoping other parents will treat water safety with the seriousness it demands."),
        P("Drowning remains a leading cause of accidental death among young children, and it often happens quickly and silently, safety advocates say."),
        P("The parents urge families to layer protections: constant adult supervision near water, swimming lessons, four-sided fencing around pools, and properly fitted life jackets on boats."),
        P("&ldquo;It can happen to anyone, in seconds,&rdquo; the family said, adding that they want other parents to treat water safety as seriously as they would a car seat."),
        N("Water-safety groups offer free guidance on supervision, barriers and life-jacket fit ahead of the summer season."),
    ])

add(slug="trump-accounts", file="trump-accounts.html", kicker="PERSONAL FINANCE", topic="Trump Accounts", cat="PERSONAL FINANCE",
    headline="Millions of babies getting $1K on July 4 with a Trump Account",
    author="Medora Lee", org="USA TODAY", date="July 3, 2026, 5:03 a.m. ET",
    hero="t-baby-flag.jpg", thumb="t-baby-flag.jpg", hero_alt="A baby with an American flag",
    caption="A new federal savings program launches July 4. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="Trump Accounts launch July 4 with a $1,000 deposit for each eligible newborn. Here's how to sign up.",
    ai_lead="A new federal savings program branded as &ldquo;Trump Accounts&rdquo; launches July 4, with a $1,000 deposit for each eligible newborn enrolled.",
    ai_q=["Who is eligible for a Trump Account?","How do parents sign up?","How does the $1,000 grow over time?"],
    blocks=[
        P("A new federal savings program known as Trump Accounts launches July 4, depositing $1,000 for each eligible newborn that is enrolled."),
        P("The accounts are designed to give children a financial head start, with the initial government contribution able to grow over time and be supplemented by family deposits."),
        P("Parents will need to complete an enrollment process to claim the deposit for a qualifying newborn. Officials have published guidance on eligibility and how to sign up."),
        P("Financial advisers say the long time horizon is the program&rsquo;s biggest advantage, though families should review the specific rules on contributions and withdrawals."),
        N("Full eligibility and enrollment details are available through the program&rsquo;s official guidance."),
    ])

add(slug="iu-workforce", file="iu-workforce.html", kicker="EDUCATION", topic="Indiana University", cat="EDUCATION",
    headline="Indiana&rsquo;s workforce starts at IU campuses",
    author="Indiana University", org="Sponsored Content", date="July 3, 2026",
    hero="h-iu.jpg", thumb="t-school.jpg", hero_alt="A university campus building",
    caption="Indiana University says it is connecting students to employers before graduation. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="Indiana University is positioning its campuses as a starting point for the state's workforce.",
    ai_lead="Indiana University says it is positioning its campuses as a starting point for the state&rsquo;s workforce, connecting students with employers before they graduate.",
    ai_q=["Which fields are most in demand?","How does IU connect students to jobs?","Why keep graduates in Indiana?"],
    blocks=[
        P("Indiana University says it is positioning its campuses as a launching point for the state&rsquo;s workforce, connecting students with employers well before graduation."),
        P("Through expanded internships, apprenticeships and industry partnerships, the university aims to keep more graduates living and working in Indiana."),
        P("Administrators point to health care, technology and advanced manufacturing as areas of particular demand across the state."),
        P("The effort reflects a broader push by public universities to demonstrate a direct link between higher education and local economic growth."),
        N("This story is sponsored content produced in partnership with Indiana University."),
    ])

add(slug="messi-cape-verde", file="messi-cape-verde.html", kicker="WORLD CUP", topic="World Cup", cat="WORLD CUP",
    headline="Lionel Messi faces underdog Cape Verde in a win-or-go-home contest",
    author="Safid Deen", org="USA TODAY", date="July 3, 2026, 11:03 a.m. ET",
    hero="t-soccer.jpg", thumb="t-soccer.jpg", hero_alt="A soccer player in a stadium",
    caption="Argentina meet Cape Verde in a knockout match in Miami. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="Lionel Messi and Argentina face underdog Cape Verde in a win-or-go-home World Cup match in Miami.",
    ai_lead="Lionel Messi and Argentina face underdog Cape Verde in a win-or-go-home match in Miami, with a place in the next round on the line.",
    ai_q=["When does the match kick off?","How did Cape Verde reach this stage?","Are Argentina the favorites?"],
    blocks=[
        P("MIAMI. Lionel Messi and Argentina face underdog Cape Verde in a win-or-go-home contest, with a place in the next round on the line."),
        P("Cape Verde, one of the tournament&rsquo;s smallest nations by population, has already exceeded expectations to reach this stage."),
        P("Argentina enter as heavy favorites, but knockout football offers no guarantees, and a single mistake can end a campaign."),
        P("Kickoff is set for Friday in Miami. Stay tuned for updates from all of the day&rsquo;s games."),
        N("This is a developing story and will be updated with results from Friday&rsquo;s fixtures."),
    ])

add(slug="nancy-guthrie", file="nancy-guthrie.html", kicker="NEWS", topic="Investigation", cat="NEWS",
    headline="Ransom note suggests how Nancy Guthrie died, article says",
    author="USA TODAY Network", org="USA TODAY", date="July 3, 2026",
    hero="h-nancy.jpg", thumb="s-investigation.jpg", hero_alt="Police investigation scene",
    caption="Investigators are examining evidence in the case. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="A ransom note is offering investigators new clues in the death of Nancy Guthrie, according to an article.",
    ai_lead="A ransom note is offering investigators new clues about how Nancy Guthrie died, according to an article citing people familiar with the case.",
    ai_q=["What does the note reportedly show?","Have any charges been filed?","What are investigators asking the public?"],
    blocks=[
        P("A ransom note is offering investigators new clues about how Nancy Guthrie died, according to an article citing people familiar with the case."),
        P("Authorities have released limited details as the investigation continues, and no charges tied to the note have been announced."),
        P("The document is one of several pieces of evidence being examined, the article said."),
        P("Officials have asked anyone with information to come forward as they work to establish a timeline."),
        N("Details remain limited and the investigation is ongoing. This is a developing story."),
    ])

add(slug="si-swimsuit", file="si-swimsuit.html", kicker="ENTERTAINMENT", topic="Sports Illustrated", cat="ENTERTAINMENT",
    headline="Sports Illustrated Swimsuit cover stars revealed: See the photos",
    author="Anika Reed", org="USA TODAY", date="July 2, 2026",
    hero="h-swimsuit.jpg", thumb="s-swimsuit.jpg", hero_alt="A beach on a summer day",
    caption="Sports Illustrated unveiled this year&rsquo;s Swimsuit Issue cover stars. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="Sports Illustrated has revealed this year's Swimsuit Issue cover stars across its platforms.",
    ai_lead="Sports Illustrated has revealed this year&rsquo;s Swimsuit Issue cover stars, unveiling the images across its platforms.",
    ai_q=["Who are this year&rsquo;s cover stars?","How has the franchise changed?","Where can I see the full gallery?"],
    blocks=[
        P("Sports Illustrated has revealed this year&rsquo;s Swimsuit Issue cover stars, unveiling the images across its platforms."),
        P("The franchise, long a summer fixture, has in recent years emphasized a wider range of models and cover choices."),
        P("The reveal was accompanied by behind-the-scenes photos and interviews with the featured cover stars."),
        P("The full gallery is available through the magazine&rsquo;s official channels."),
        N("See the complete set of cover images on Sports Illustrated&rsquo;s official site."),
    ])

add(slug="tesla-evs", file="tesla-evs.html", kicker="EVS", topic="Tesla", cat="MONEY",
    headline="Tesla has a glut of unsold EVs. Here&rsquo;s what they are doing about it",
    author="Keith Laing", org="USA TODAY", date="July 2, 2026, 1:38 p.m. ET",
    hero="h-tesla.jpg", thumb="s-tesla.jpg", hero_alt="An electric car charging",
    caption="Tesla delivered more cars than it built in the second quarter of 2026. <span style=\"font-style:italic\">Photo via Flickr / Creative Commons</span>",
    desc="Tesla is reducing a backlog of unsold EVs by delivering more cars than it produced in the second quarter of 2026.",
    ai_lead="Tesla is reducing a backlog of unsold electric vehicles by selling more cars than it produced in the second quarter of 2026, aided by a slight uptick in EV interest.",
    ai_q=["How many more cars did Tesla deliver than it built?","How big was the inventory glut?","Why did EV interest tick up?"],
    blocks=[
        P("Tesla is working through a backlog of unsold electric vehicles by delivering more cars than it produced in the second quarter of 2026."),
        P("The company reported delivering 480,126 EVs globally in the spring of 2026, while producing 451,758 in the same period, according to figures it released July 2."),
        P("Selling roughly 28,000 more cars than it built allowed Tesla to draw down a glut of unsold inventory it had been carrying at the start of the year, aided by a slight uptick in EV interest amid rising gas prices."),
        P("The nation&rsquo;s largest electric-car seller has faced a more competitive market, and the inventory drawdown is one sign of how it is adjusting."),
        N("Figures are drawn from Tesla&rsquo;s production and delivery report released July 2, 2026."),
    ])

# ---------------------------------------------------------------- write
out_dir = pathlib.Path(".")
for slug, s in S.items():
    (out_dir / s["file"]).write_text(page(s), encoding="utf-8")
    print("wrote", s["file"])
print("done:", len(S), "pages")
