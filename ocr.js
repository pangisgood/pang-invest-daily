(() => {
  const CDN = 'https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';

  const aliases = {
    '381180': ['TIGER 미국필라델피아반도체나스닥', '미국필라델피아반도체나스닥', '필라델피아반도체'],
    '458730': ['TIGER 미국배당다우존스', '미국배당다우존스', '배당다우존스'],
    '486290': ['TIGER 미국나스닥100타겟데일리커버드콜', '미국나스닥100타겟데일리커버드콜', '나스닥100타겟데일리커버드콜'],
    '0046Y0': ['ACE 미국배당퀄리티', '미국배당퀄리티', '배당퀄리티'],
    '360750': ['TIGER 미국S&P500', '미국S&P500', 'S&P500'],
    '0041E0': ['KODEX 미국S&P500액티브', '미국S&P500액티브', 'S&P500액티브'],
    '0066W0': ['SOL 국제금', '국제금'],
    '494890': ['KODEX 200액티브', '200액티브'],
    '0043Y0': ['TIME 차이나AI테크액티브', '차이나AI테크액티브', '차이나AI'],
    '0172V0': ['1Q 은액티브', '은액티브']
  };

  const normalize = s => (s || '')
    .replace(/\s+/g, '')
    .replace(/[·ㆍ∙]/g, '')
    .replace(/[|]/g, 'I')
    .toUpperCase();

  async function loadTesseract() {
    if (window.Tesseract) return;
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = CDN;
      s.onload = resolve;
      s.onerror = () => reject(new Error('OCR 라이브러리를 불러오지 못했습니다.'));
      document.head.appendChild(s);
    });
  }

  function nearbyBlock(raw, alias) {
    const nRaw = normalize(raw);
    const nAlias = normalize(alias);
    const pos = nRaw.indexOf(nAlias);
    if (pos < 0) return '';
    // normalize() removes characters, so exact positions differ from raw.
    // Search line-by-line instead and return a few lines around the best match.
    const lines = raw.split(/\n+/).map(x => x.trim()).filter(Boolean);
    const idx = lines.findIndex(line => normalize(line).includes(nAlias));
    if (idx < 0) return '';
    return lines.slice(Math.max(0, idx - 1), idx + 7).join('\n');
  }

  function findHoldingBlock(raw, code) {
    const names = aliases[code] || [];
    for (const name of names) {
      const b = nearbyBlock(raw, name);
      if (b) return b;
    }
    return '';
  }

  function moneyNumbers(text) {
    return [...text.matchAll(/([+-]?\s*\d{1,3}(?:,\d{3})+|[+-]?\s*\d{4,})\s*원?/g)]
      .map(m => Number(m[1].replace(/[,\s]/g, '')))
      .filter(Number.isFinite);
  }

  function extractQty(block) {
    const patterns = [
      /보유(?:수량)?\s*[:：]?\s*([\d,.]+)\s*주/i,
      /([\d,.]+)\s*주\b/i,
      /수량\s*[:：]?\s*([\d,.]+)/i
    ];
    for (const p of patterns) {
      const m = block.match(p);
      if (m) return Number(m[1].replace(/,/g, ''));
    }
    return null;
  }

  function extractAvg(block) {
    const patterns = [
      /평균(?:매입)?단가\s*[:：]?\s*([\d,]+)\s*원?/i,
      /매입단가\s*[:：]?\s*([\d,]+)\s*원?/i
    ];
    for (const p of patterns) {
      const m = block.match(p);
      if (m) return Number(m[1].replace(/,/g, ''));
    }
    return null;
  }

  function inferFromAmounts(block, code) {
    const price = window.DATA?.etfs?.[code]?.price;
    if (!price) return {};
    const nums = moneyNumbers(block).filter(n => Math.abs(n) >= 1000);
    if (!nums.length) return {};

    // 가장 큰 양수를 평가금액 후보로 보고 현재가로 수량을 추정.
    const positives = nums.filter(n => n > 0);
    const evalAmount = positives.length ? Math.max(...positives) : null;
    if (!evalAmount) return {};

    const roughQty = evalAmount / price;
    const rounded = Math.round(roughQty);
    const qty = Math.abs(roughQty - rounded) <= 0.18 ? rounded : Number(roughQty.toFixed(4));

    // + / -가 붙은 금액 중 평가액보다 작은 값을 손익 후보로 사용.
    const signedMatches = [...block.matchAll(/([+-])\s*([\d]{1,3}(?:,\d{3})+|[\d]{4,})\s*원?/g)]
      .map(m => (m[1] === '-' ? -1 : 1) * Number(m[2].replace(/,/g, '')))
      .filter(n => Number.isFinite(n) && Math.abs(n) < evalAmount);
    const profit = signedMatches.length ? signedMatches[0] : null;
    const avg = (profit != null && qty) ? Math.round((evalAmount - profit) / qty) : null;

    return { qty, avg, evalAmount, profit };
  }

  function parseOCR(raw) {
    const result = {};
    for (const code of Object.keys(aliases)) {
      const block = findHoldingBlock(raw, code);
      if (!block) continue;

      let qty = extractQty(block);
      let avg = extractAvg(block);
      const inferred = inferFromAmounts(block, code);

      if (qty == null && inferred.qty != null) qty = inferred.qty;
      if (avg == null && inferred.avg != null) avg = inferred.avg;

      result[code] = { qty, avg, block };
    }
    return result;
  }

  function ensureUI() {
    const dialog = document.getElementById('holdingDialog');
    if (!dialog || dialog.dataset.ocrReady) return;
    dialog.dataset.ocrReady = '1';

    const modal = dialog.querySelector('.modal');
    const formList = dialog.querySelector('#holdingForms');
    if (!modal || !formList) return;

    const box = document.createElement('div');
    box.style.cssText = 'margin:12px 0;padding:12px;border:1px solid #eceaf2;border-radius:14px;background:#faf9fd;';
    box.innerHTML = `
      <div style="font-size:12px;font-weight:800;margin-bottom:5px;">📷 캡처로 보유정보 불러오기</div>
      <div style="font-size:11px;color:#83838d;line-height:1.5;margin-bottom:9px;">
        토스/증권앱 보유자산 캡처를 선택하면 이 브라우저에서만 OCR로 읽습니다.
        자동 인식 후 값이 맞는지 확인하고 기존 '저장' 버튼을 눌러주세요.
      </div>
      <input id="holdingOcrFile" type="file" accept="image/*" multiple style="display:none;">
      <button id="holdingOcrBtn" type="button"
        style="width:100%;border:0;background:#6f4bd8;color:white;border-radius:11px;padding:10px;font-weight:800;">
        캡처 선택
      </button>
      <div id="holdingOcrStatus" style="font-size:11px;color:#83838d;margin-top:8px;line-height:1.5;"></div>
      <details id="holdingOcrRawWrap" style="display:none;margin-top:8px;">
        <summary style="font-size:11px;color:#6f4bd8;cursor:pointer;">인식 원문 보기</summary>
        <pre id="holdingOcrRaw" style="white-space:pre-wrap;font-size:10px;max-height:180px;overflow:auto;background:white;border-radius:10px;padding:8px;"></pre>
      </details>
    `;
    formList.parentNode.insertBefore(box, formList);

    const fileInput = box.querySelector('#holdingOcrFile');
    const btn = box.querySelector('#holdingOcrBtn');
    const status = box.querySelector('#holdingOcrStatus');
    const rawWrap = box.querySelector('#holdingOcrRawWrap');
    const rawPre = box.querySelector('#holdingOcrRaw');

    btn.onclick = () => fileInput.click();

    fileInput.onchange = async () => {
      const files = [...fileInput.files];
      if (!files.length) return;

      btn.disabled = true;
      btn.textContent = 'OCR 준비 중...';
      status.textContent = '첫 실행은 한글 OCR 데이터 다운로드 때문에 조금 걸릴 수 있어요.';

      try {
        await loadTesseract();
        let allText = '';

        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          status.textContent = `${i + 1}/${files.length}번째 캡처 인식 중...`;
          const { data } = await Tesseract.recognize(file, 'kor+eng', {
            logger: m => {
              if (m.status === 'recognizing text' && typeof m.progress === 'number') {
                status.textContent = `${i + 1}/${files.length}번째 캡처 인식 중... ${Math.round(m.progress * 100)}%`;
              }
            }
          });
          allText += '\n' + (data?.text || '');
        }

        rawPre.textContent = allText.trim();
        rawWrap.style.display = 'block';

        const parsed = parseOCR(allText);
        let matched = 0;
        let filled = 0;

        for (const [code, info] of Object.entries(parsed)) {
          matched++;
          const q = document.querySelector(`[data-q="${code}"]`);
          const a = document.querySelector(`[data-a="${code}"]`);
          if (q && info.qty != null && info.qty !== '') {
            q.value = info.qty;
            q.style.outline = '2px solid #b9a9ff';
            filled++;
          }
          if (a && info.avg != null && info.avg !== '') {
            a.value = Math.round(info.avg);
            a.style.outline = '2px solid #b9a9ff';
          }
        }

        if (matched) {
          status.innerHTML = `<b style="color:#12805c">${matched}개 종목을 찾았어요.</b> 수량 ${filled}개를 자동 입력했습니다. 값 확인 후 아래 '저장'을 눌러주세요.`;
        } else {
          status.innerHTML = `<b style="color:#b26a00">종목을 자동 매칭하지 못했어요.</b> '인식 원문 보기'에서 OCR 결과를 확인해 주세요.`;
        }
      } catch (e) {
        console.error(e);
        status.innerHTML = `<b style="color:#c33">OCR 실패:</b> ${e?.message || e}`;
      } finally {
        btn.disabled = false;
        btn.textContent = '다른 캡처 선택';
        fileInput.value = '';
      }
    };
  }

  // 기존 '보유정보' 버튼이 dialog 내용을 만든 직후 OCR UI가 보이도록 감시.
  const observer = new MutationObserver(ensureUI);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener('DOMContentLoaded', ensureUI);
  ensureUI();
})();
