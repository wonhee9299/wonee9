import urllib.request, urllib.parse, urllib.error, re, time, datetime, json, html, concurrent.futures as cf, collections
PC='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
KST=datetime.timezone(datetime.timedelta(hours=9))
NOW=datetime.datetime.now(KST); WIN=datetime.timedelta(days=7); SINCE=NOW-WIN
CATS={
 '등산':r'등산|아웃도어|트레킹|고어텍스|블랙야크|노스페이스|코오롱스포츠|\bK2\b|네파|아이더|밀레|컬럼비아|머렐|캠프라인|등산화|등산복|등산스틱|백패킹',
 '러닝':r'러닝화|런닝화|러닝복|런닝복|러닝 |런닝 |마라톤|조깅|호카|아식스|페가수스|보메로|인빈서블|알파플라이|베이퍼플라이|온러닝|가민|뉴발란스',
 '수영':r'수영|수영복|수경|수모|아레나|스피도|배럴|래쉬가드|오리발',
 '골프':r'골프|퍼터|웨지|타이틀리스트|캘러웨이|테일러메이드|젝시오|볼빅|거리측정기|그린피',
 '자전거':r'자전거|따릉이|로드바이크|MTB|전기자전거|가민 엣지|시마노|브롬톤|미니벨로|삼천리|알톤',
 '트레일러닝':r'트레일|스피드크로스|스피드고트',
 '놀이동산':r'에버랜드|롯데월드|서울랜드|레고랜드|경주월드|이월드|캐리비안베이|오션월드|워터파크|자유이용권|아쿠아리움',
 '키즈카페':r'키즈카페|키즈 카페|챔피언 키즈|바운스|플레이타임|점핑|키즈랜드|키즈존|실내놀이터',
}
CRE={k:re.compile(v,re.I) for k,v in CATS.items()}
def get(u,enc=None):
    last=None
    for i in range(5):
        try:
            b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':PC,'Accept-Language':'ko-KR,ko;q=0.9'}),timeout=20).read()
            if enc: return b.decode(enc,'ignore')
            try: return b.decode('utf-8')
            except: return b.decode('euc-kr','ignore')
        except urllib.error.HTTPError as e:
            if e.code in (403,404,430): return ''
            last=e; time.sleep(1)
        except Exception as e: last=e; time.sleep(1)
    return ''
def clean(s): return html.unescape(re.sub(r'<[^>]+>','',s)).strip()
def today_or(dstr):
    """parse 'HH:MM' as today, 'MM-DD' as this year, 'YY-MM-DD','YY.MM.DD','YYYY.MM.DD','YYYY-MM-DD hh:mm:ss'"""
    dstr=dstr.strip()
    m=re.fullmatch(r'(\d\d):(\d\d)',dstr)
    if m: return NOW.replace(hour=int(m[1]),minute=int(m[2]),second=0)
    m=re.fullmatch(r'(\d\d)[-./](\d\d)',dstr)
    if m:
        d=NOW.replace(month=int(m[1]),day=int(m[2]),hour=0,minute=0,second=0)
        return d if d<=NOW else d.replace(year=NOW.year-1)
    m=re.fullmatch(r'(\d\d)[-./](\d\d)[-./](\d\d)',dstr)
    if m: return datetime.datetime(2000+int(m[1]),int(m[2]),int(m[3]),tzinfo=KST)
    m=re.match(r'(\d{4})[-./](\d\d)[-./](\d\d)(?:[ T](\d\d):(\d\d)(?::(\d\d))?)?',dstr)
    if m: return datetime.datetime(int(m[1]),int(m[2]),int(m[3]),int(m[4] or 0),int(m[5] or 0),tzinfo=KST)
    return None

def scan_pages(name,url_fn,parse_fn,maxpages=90,delay=0.3):
    posts={};
    for p in range(1,maxpages+1):
        h=get(url_fn(p));
        if not h: break
        rows=parse_fn(h);
        if not rows: break
        older=0
        for pid,title,dt in rows:
            if dt is None: continue
            if dt<SINCE: older+=1; continue
            posts[pid]=(title,dt)
        if older>=len(rows)*0.8: break
        time.sleep(delay)
    return posts

def p_clien(h):
    out=[]
    for blk in re.findall(r'<div class="list_item symph_row.*?(?=<div class="list_item symph_row|<div class="list_infomation|$)',h,re.S):
        t=re.search(r'class="list_subject"[^>]*title="([^"]*)"',blk); ts=re.search(r'class="timestamp">([^<]*)<',blk); pid=re.search(r'data-board-sn=(\d+)',blk)
        if t and ts and pid: out.append((pid[1],html.unescape(t[1]),today_or(ts[1])))
    return out
def p_ruliweb(h):
    out=[]
    for blk in re.findall(r'<tr class="table_body.*?</tr>',h,re.S):
        if 'best' in blk[:60] and 'inside' in blk[:60]: continue
        t=re.search(r'class="subject_link deco"[^>]*href="[^"]*/read/(\d+)[^"]*"[^>]*>\s*<strong>(.*?)</strong>',blk,re.S); ts=re.search(r'class="time">\s*([^<]*?)\s*<',blk)
        if t and ts: out.append((t[1],clean(t[2]),today_or(ts[1])))
    return out
def p_dealbada(h):
    out=[]
    for blk in re.findall(r'<tr.*?</tr>',h,re.S):
        t=re.search(r'class="td_subject">\s*<a href="[^"]*wr_id=(\d+)[^"]*"\s*>(.*?)</a>',blk,re.S); ts=re.search(r'class="td_date">([^<]*)<',blk); cat=re.search(r'class="bo_cate_link">([^<]*)<',blk)
        if t and ts: out.append((t[1],('['+cat[1]+'] ' if cat else '')+clean(t[2]),today_or(ts[1])))
    return out
def p_bbasak(h):
    out=[]
    for blk in re.findall(r'<tr.*?</tr>',h,re.S):
        t=re.search(r'class="tit">.*?wr_id=(\d+)[^"]*">(.*?)</a>',blk,re.S); ts=re.search(r'class="etc2 fthm">([\d:\-. ]+)<',blk)
        if t and ts: out.append((t[1],clean(t[2]),today_or(ts[1])))
    return out
def p_eomisae(h):
    out=[]
    for blk in re.findall(r'<tr.*?</tr>',h,re.S):
        t=re.search(r'class="title"[^>]*>(.*?)</td>',blk,re.S); pid=re.search(r'href="/fs/(\d+)"',blk); ts=re.search(r'<td>(\d\d\.\d\d\.\d\d|\d\d:\d\d)</td>',blk)
        if t and pid and ts: out.append((pid[1],clean(t[1]),today_or(ts[1])))
    return out
def p_arca(h):
    out=[]
    for blk in re.findall(r'<div class="vrow .*?(?=<div class="vrow |<div class="vrow-bottom-wrap|$)',h,re.S):
        if 'notice' in blk[:80]: continue
        t=re.search(r'<a class="title[^"]*" href="/b/hotdeal/(\d+)[^"]*">(.*?)</a>',blk,re.S); ts=re.search(r'datetime="([^"]+)"',blk); cat=re.search(r'class="badge" href="/b/hotdeal\?category=[^"]*">([^<]*)<',blk); store=re.search(r'class="deal-store">([^<]*)<',blk)
        if t and ts:
            dt=datetime.datetime.fromisoformat(ts[1].replace('Z','+00:00')).astimezone(KST)
            title=re.sub(r'<span class="comment-count">.*?</span>','',t[2],flags=re.S); title=re.sub(r'<div class="vrow-bottom.*','',title,flags=re.S)
            out.append((t[1],('['+cat[1]+'] ' if cat else '')+('['+store[1].strip()+'] ' if store else '')+clean(title),dt))
    return out

def p_ruliweb(h):
    out=[]
    for blk in h.split('<tr class="table_body')[1:]:
        if blk.startswith(' best') or blk.startswith('best'): 
            if 'inside' in blk[:40]: continue
        a=re.search(r'<a class="subject_link deco"[^>]*href="[^"]*/read/(\d+)[^"]*"[^>]*>(.*?)</a>\s*</td>',blk,re.S)
        tm=re.search(r'<td class="time">(.*?)</td>',blk,re.S)
        if not (a and tm): continue
        tok=re.search(r'\d{4}\.\d\d\.\d\d|\d\d:\d\d',tm[1])
        if not tok: continue
        title=re.sub(r'<a class="num_reply".*?</a>','',a[2],flags=re.S)
        out.append((a[1],clean(title),today_or(tok[0])))
    return out
def p_bbasak(h):
    out=[]
    for blk in h.split('<tr')[1:]:
        t=re.search(r'class="tit">.*?wr_id=(\d+)[^"]*">(.*?)</a>',blk,re.S)
        if not t: continue
        cells=re.findall(r'class="etc2 fthm">([^<]*)<',blk)
        d=next((c for c in cells if re.fullmatch(r'\d\d-\d\d-\d\d',c.strip()) and not c.startswith('70')),None)
        if not d: d=next((c[:5] for c in cells if re.fullmatch(r'\d\d:\d\d:\d\d',c.strip())),None)
        if d: out.append((t[1],clean(t[2]),today_or(d)))
    return out
def p_eomisae(h):
    out=[]
    for blk in h.split('<tr')[1:]:
        a=re.search(r'<a class="pjax" href="/fs/(\d+)">(.*?)</a>',blk,re.S); ts=re.search(r'<td>(\d\d\.\d\d\.\d\d|\d\d:\d\d)</td>',blk)
        if a and ts: out.append((a[1],clean(a[2]),today_or(ts[1])))
    return out
def p_damoang(h):
    out=[]
    for blk in re.split(r'(?=<a href="/economy/\d+)',h)[1:]:
        pid=re.match(r'<a href="/economy/(\d+)',blk); t=re.search(r'class="truncate post-title[^"]*" title="([^"]*)"',blk); ts=re.search(r'>(\d\d\.\d\d|\d\d:\d\d)</span>',blk)
        if pid and t and ts: out.append((pid[1],html.unescape(t[1]),today_or(ts[1])))
    return out
SITES={
 '클리앙 알뜰구매':(lambda p:f'https://www.clien.net/service/board/jirum?po={p-1}',p_clien),
 '루리웹 핫딜':(lambda p:f'https://bbs.ruliweb.com/market/board/1020?page={p}',p_ruliweb),
 '딜바다 국내핫딜':(lambda p:f'https://www.dealbada.com/bbs/board.php?bo_table=deal_domestic&page={p}',p_dealbada),
 '빠삭 국내':(lambda p:f'https://bbasak.com/bbs/board.php?bo_table=bbasak1&page={p}',p_bbasak),
 '어미새 fs':(lambda p:f'https://eomisae.co.kr/fs?page={p}',p_eomisae),
 '아카라이브 핫딜':(lambda p:f'https://arca.live/b/hotdeal?p={p}',p_arca),
 '다모앙 알뜰구매':(lambda p:f'https://damoang.net/economy?page={p}',p_damoang),
}
# 뽐뿌: 검색 기반
PKW={'등산':['등산','아웃도어','노스페이스','블랙야크','트레킹'],'러닝':['러닝','런닝','마라톤','호카','아식스'],'수영':['수영','수영복','수경','래쉬가드'],'골프':['골프','퍼터','골프공'],
     '자전거':['자전거','따릉이','전기자전거'],'트레일러닝':['트레일'],'놀이동산':['에버랜드','롯데월드','워터파크','자유이용권','레고랜드'],'키즈카페':['키즈카페','실내놀이터','점핑']}
def ppomppu():
    res={c:{} for c in PKW}; total=0
    for cat,kws in PKW.items():
        for kw in kws:
            k=urllib.parse.quote(kw.encode('euc-kr'))
            for p in range(1,6):
                h=get(f'https://www.ppomppu.co.kr/search_bbs.php?search_type=sub_memo&keyword={k}&order_type=date&page_no={p}','euc-kr')
                if not h: break
                blks=re.findall(r'<div class="content">(.*?)<p class="desc">(.*?)</p>',h,re.S); old=0
                if not blks: break
                for body,desc in blks:
                    m=re.search(r'href=/zboard/view\.php\?id=(ppomppu|ppomppu4|ppomppu8)&no=(\d+)[^>]*>(.*?)</a>',body,re.S)
                    d=re.search(r'<span>(20\d\d\.\d\d\.\d\d)</span>',desc)
                    if not d: continue
                    dt=today_or(d[1])
                    if dt<SINCE: old+=1; continue
                    if m and CRE[cat].search(clean(m[3])): res[cat][m[1]+m[2]]=(clean(m[3]),dt)
                if old>=len(blks)*0.8: break
                time.sleep(0.3)
    return res
def run_site(item):
    name,(uf,pf)=item
    posts=scan_pages(name,uf,pf)
    bycat={c:{pid:v for pid,v in posts.items() if CRE[c].search(v[0])} for c in CATS}
    return name,len(posts),bycat
out={}
with cf.ThreadPoolExecutor(7) as ex:
    futs=[ex.submit(run_site,it) for it in SITES.items()]; futs.append(ex.submit(lambda:('뽐뿌게시판(검색)',None,ppomppu())))
    for f in futs:
        name,total,bycat=f.result(); out[name]={'total7d':total,'cats':{c:[(t,d.strftime('%m-%d')) for t,d in sorted(v.values(),key=lambda x:-x[1].timestamp())] for c,v in bycat.items()}}
        print(f'\n##### {name}  최근7일 전체 {total}건');
        for c in CATS:
            L=out[name]['cats'][c]; print(f'  {c:<6} {len(L):>3}건  ' + ' | '.join(t[:38] for t,_ in L[:3]))
        print(flush=True)
json.dump(out,open('dealscan2.json','w'),ensure_ascii=False,indent=1)
print('SCAN DONE')
